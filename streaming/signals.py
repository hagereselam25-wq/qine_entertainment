import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.db.models import Sum

from .models import UserProfile, StreamingContent, StreamViewLog, StreamingAnalytics
from .utils import convert_mp4_to_hls

# -------------------- User Profile Signals --------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


# -------------------- HLS Conversion Signal --------------------
@receiver(post_save, sender=StreamingContent)
def handle_hls_conversion(sender, instance, created, **kwargs):
    # Only convert if it's a new upload or missing hls_folder
    if instance.video_file and not instance.hls_folder and instance.video_file.name.lower().endswith('.mp4'):
        try:
            hls_folder, _ = convert_mp4_to_hls(
                mp4_path=os.path.join(settings.MEDIA_ROOT, instance.video_file.name),
                output_dir=os.path.join(settings.MEDIA_ROOT, 'hls'),
                content_id=instance.id
            )
            instance.hls_folder = os.path.relpath(hls_folder, settings.MEDIA_ROOT).replace("\\", "/")
            instance.save(update_fields=['hls_folder'])
        except Exception as e:
            print(_("HLS conversion failed:"), e)


# -------------------- Update Total Watch Time --------------------
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


# -------------------- Update Streaming Analytics --------------------
@receiver(post_save, sender=StreamViewLog)
def update_streaming_analytics(sender, instance, **kwargs):
    content = instance.content

    # Aggregate data from StreamViewLog
    agg = StreamViewLog.objects.filter(content=content).aggregate(
        total_views=Sum('views'),
        total_watch_time=Sum('watch_time_seconds')
    )

    total_views = agg['total_views'] or 0
    total_watch_time = agg['total_watch_time'] or 0

    # Compute average completion rate
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