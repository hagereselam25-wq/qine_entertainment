import time
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings
import time
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings

def generate_signed_url(video_id, base_url, expire_seconds=300):
    """
    Generate a signed URL for HLS videos (.m3u8).
    For MP4 files, return the plain URL.
    """
    if base_url.lower().endswith('.mp4'):
        # No signing needed for direct MP4
        return base_url

    # --- HLS signing ---
    expires = int(time.time()) + expire_seconds
    data = f"{video_id}:{expires}"

    signature = hmac.new(
        settings.SIGNED_URL_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    query_params = {
        "video_id": video_id,
        "expires": expires,
        "signature": signature,
    }

    return f"{base_url}?{urlencode(query_params)}"


def validate_signed_url(video_id, expires, signature):
    """
    Verify that a signed URL is valid (used for HLS).
    """
    if int(expires) < time.time():
        return False

    expected_signature = hmac.new(
        settings.SIGNED_URL_SECRET.encode(),
        f"{video_id}:{expires}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)
