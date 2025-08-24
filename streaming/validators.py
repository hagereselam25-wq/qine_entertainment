import os
from django.core.exceptions import ValidationError

# Allowed video extensions (FFmpeg supports many, you can expand)
ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"]

def validate_video_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported file type: {ext}. Allowed formats: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")