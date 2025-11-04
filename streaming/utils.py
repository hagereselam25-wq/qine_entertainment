import os
import subprocess
import time
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings
from django.core.exceptions import ValidationError

# ------------------- Signed URL Utilities -------------------
def generate_signed_url(video_id, base_url, expire_seconds=300):
    # generate a signed URL for HLS videos (.m3u8)
    if base_url.lower().endswith('.mp4'):
        return base_url

    expires = int(time.time()) + expire_seconds
    data = f"{video_id}:{expires}"
    signature = hmac.new(
        settings.SIGNED_URL_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    query_params = {"video_id": video_id, "expires": expires, "signature": signature}
    return f"{base_url}?{urlencode(query_params)}"

def validate_signed_url(video_id, expires, signature):
    # Verify that a signed URL is valid
    if int(expires) < time.time():
        return False

    expected_signature = hmac.new(
        settings.SIGNED_URL_SECRET.encode(),
        f"{video_id}:{expires}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)

# ------------------- Video Validation -------------------
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm']

def validate_video_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported video format '{ext}'. Allowed: {ALLOWED_VIDEO_EXTENSIONS}")

# ------------------- HLS Conversion -------------------
def convert_video_to_hls(video_path, output_dir, content_id, verbose=True, encrypt=False, key_info_file=None):
    """
    Convert any supported video to HLS (.m3u8). Optionally apply AES-128 encryption.
    Output: MEDIA_ROOT/hls/<content_id>/
    """

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Skip if already HLS
    if video_path.lower().endswith(".m3u8"):
        hls_folder = os.path.dirname(video_path)
        master_playlist = video_path
        if verbose:
            print(f"[DEBUG] File is already HLS. Skipping conversion for {content_id}")
        return hls_folder, master_playlist

    # Validate video using ffprobe
    try:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        if "video" not in probe_result.stdout:
            raise ValueError(f"The file is not a valid video: {video_path}")
        if verbose:
            print(f"[DEBUG] ffprobe check passed for {video_path}")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"ffprobe failed for {video_path}: {e.stderr}")

    # Ensure output folder exists
    hls_folder = os.path.join(output_dir, str(content_id))
    os.makedirs(hls_folder, exist_ok=True)

    master_playlist = os.path.join(hls_folder, "master.m3u8")
    segment_pattern = os.path.join(hls_folder, "file_%03d.ts")

    # FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-c:v", "h264",
        "-c:a", "aac",
        "-preset", "fast",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", segment_pattern
    ]

    # Add encryption if requested
    if encrypt and key_info_file:
        cmd.extend(["-hls_key_info_file", key_info_file])

    # Append master playlist at the end
    cmd.append(master_playlist)

    if verbose:
        print(f"[DEBUG] Running ffmpeg command: {' '.join(cmd)}")

    try:
        process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if verbose:
            print(f"[DEBUG] ffmpeg output:\n{process.stderr.decode('utf-8')}")
            print(f"[INFO] HLS conversion complete for content ID {content_id}")
    except subprocess.CalledProcessError as e:
        error_output = e.stderr.decode("utf-8") if e.stderr else str(e)
        print(f"[ERROR] HLS conversion failed for content ID {content_id}:\n{error_output}")
        raise RuntimeError(f"HLS conversion failed: {error_output}")

    return hls_folder, master_playlist
