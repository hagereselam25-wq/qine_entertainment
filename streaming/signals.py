import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Sum

from .models import UserProfile, StreamingContent, StreamViewLog
from .utils import convert_video_to_hls

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import StreamingContent
from .utils import convert_video_to_hls

import os
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import StreamingContent
from .utils import convert_video_to_hls
from django.core.files.base import ContentFile
import secrets

import os
import uuid
import secrets
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import StreamingContent
from .utils import convert_video_to_hls

import os
import uuid
import secrets
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StreamingContent
from .utils import convert_video_to_hls

@receiver(post_save, sender=StreamingContent)
def convert_video_to_hls_signal(sender, instance, created, **kwargs):
    """
    Automatically convert uploaded videos to HLS with AES-128 encryption.
    """

    if instance.video_file and not instance.hls_folder:
        try:
            video_path = instance.video_file.path
            output_dir = os.path.join(settings.MEDIA_ROOT, 'hls')
            os.makedirs(output_dir, exist_ok=True)

            # --- AES-128 key generation ---
            key = secrets.token_bytes(16)  # 16 bytes = 128 bits
            key_folder = os.path.join(output_dir, 'keys')
            os.makedirs(key_folder, exist_ok=True)
            key_filename = f"{uuid.uuid4()}.key"
            key_path = os.path.join(key_folder, key_filename)

            # Save key to disk
            with open(key_path, 'wb') as f:
                f.write(key)

            # --- FFmpeg key info file ---
            key_info_filename = f"{uuid.uuid4()}_key_info.txt"
            key_info_path = os.path.join(output_dir, key_info_filename)

            # URL to serve key via Django view (must implement view to serve securely)
            key_url = f"/media/hls_keys/{key_filename}"

            # IV left empty for auto-generation
            with open(key_info_path, 'w') as f:
                f.write(f"{key_path}\n")  # local path to key for FFmpeg
                f.write(f"{key_url}\n")   # URL clients use
                f.write("\n")              # optional IV

            # --- Convert video to HLS with encryption ---
            hls_folder, _ = convert_video_to_hls(
                video_path=video_path,
                output_dir=output_dir,
                content_id=instance.id,
                key_info_file=key_info_path,
                encrypt=True,
                verbose=True
            )

            # Save HLS folder relative to MEDIA_ROOT
            instance.hls_folder = os.path.relpath(hls_folder, settings.MEDIA_ROOT).replace("\\", "/")
            instance.save(update_fields=['hls_folder'])

            print(f"[INFO] HLS conversion & encryption completed for content ID {instance.id}")

        except Exception as e:
            print("⚠️ HLS conversion failed:", e)

@receiver(post_save, sender=StreamViewLog)
def update_total_watch_time(sender, instance, **kwargs):
    """
    Update the total watch time in StreamingContent whenever a StreamViewLog changes.
    """
    total_seconds = StreamViewLog.objects.filter(content=instance.content).aggregate(
        total=Sum('watch_time_seconds')
    )['total'] or 0

    StreamingContent.objects.filter(pk=instance.content.pk).update(
        total_watch_time_seconds=total_seconds
    )



@receiver(post_save, sender=StreamViewLog)
def update_streaming_analytics(sender, instance, **kwargs):
    content = instance.content

    # aggregate data from StreamViewLog
    agg = StreamViewLog.objects.filter(content=content).aggregate(
        total_views=Sum('views'),
        total_watch_time=Sum('watch_time_seconds')
    )

    total_views = agg['total_views'] or 0
    total_watch_time = agg['total_watch_time'] or 0

    # compute average completion rate
    if total_views > 0 and content.duration_minutes > 0:
        average_completion_rate = min(
            100.0,
            round(total_watch_time / (content.duration_minutes * 60 * total_views) * 100, 2)
        )
    else:
        average_completion_rate = 0.0

    analytics, created = StreamingAnalytics.objects.get_or_create(content=content)
    analytics.total_views = total_views
    analytics.total_watch_time_seconds = total_watch_time
    analytics.average_completion_rate = average_completion_rate
    analytics.save()
