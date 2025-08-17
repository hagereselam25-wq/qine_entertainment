import os
import subprocess
import time
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings

# ------------------- Signed URL Utilities -------------------
def generate_signed_url(video_id, base_url, expire_seconds=300):
    """Generate a signed URL for HLS videos (.m3u8)."""
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
    """Verify that a signed URL is valid."""
    if int(expires) < time.time():
        return False

    expected_signature = hmac.new(
        settings.SIGNED_URL_SECRET.encode(),
        f"{video_id}:{expires}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


# ------------------- MP4 → HLS Conversion -------------------
def convert_mp4_to_hls(mp4_path, output_dir, content_id):
    """
    Convert MP4 to single-quality HLS for simplicity.
    Output directory will be MEDIA_ROOT/hls/<content_id>/
    """
    hls_folder = os.path.join(output_dir, str(content_id))
    os.makedirs(hls_folder, exist_ok=True)
    master_playlist = os.path.join(hls_folder, "master.m3u8")
    segment_pattern = os.path.join(hls_folder, "file_%03d.ts")

    cmd = [
        "ffmpeg",
        "-i", mp4_path,
        "-c:v", "h264",
        "-c:a", "aac",
        "-preset", "fast",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", segment_pattern,
        master_playlist
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"HLS conversion complete for content ID {content_id}: {master_playlist}")
    except subprocess.CalledProcessError as e:
        print(f"Error during HLS conversion for content ID {content_id}: {e}")
        raise e

    return hls_folder, master_playlist