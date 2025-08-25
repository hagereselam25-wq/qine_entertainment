from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .utils import convert_video_to_hls


SUBSCRIPTION_CHOICES = (
    ('monthly', _('Monthly')),
    ('annual', _('Annual')),
)

# -------------------- Transactions --------------------
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tx_ref = models.CharField(_("Transaction Reference"), max_length=100, unique=True)
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    email = models.EmailField(_("Email"))
    first_name = models.CharField(_("First Name"), max_length=100, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=100, blank=True)
    status = models.CharField(_("Status"), max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return f"{_('Transaction')} {self.tx_ref} - {self.status}"


# -------------------- Streaming Subscription --------------------
class StreamingSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(_("Full Name"), max_length=100)
    email = models.EmailField(_("Email"))
    subscription_type = models.CharField(_("Subscription Type"), max_length=10, choices=SUBSCRIPTION_CHOICES)
    chapa_tx_ref = models.CharField(_("Chapa Transaction Reference"), max_length=100, unique=True)
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(_("Paid"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    access_expires_at = models.DateTimeField(_("Access Expires At"), null=True, blank=True)
    qr_code = models.ImageField(_("QR Code"), upload_to='qrcodes/', blank=True, null=True)

    def has_access(self):
        return self.is_paid and self.access_expires_at and timezone.now() < self.access_expires_at

    def str(self):
        return f"{self.full_name} - {self.subscription_type}"


# -------------------- Streaming Content --------------------
from django.db import models
from django.utils.translation import gettext_lazy as _


import os
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .validators import validate_video_extension

import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .utils import convert_video_to_hls

# ------------------- Video Validator -------------------
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm']

def validate_video_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported video format '{ext}'. Allowed: {ALLOWED_VIDEO_EXTENSIONS}")


# ------------------- StreamingContent Model -------------------
class StreamingContent(models.Model):
    CATEGORY_CHOICES = [
        ('movie', _('Movie')),
        ('series', _('Series')),
        ('documentary', _('Documentary')),
        ('short', _('Short Film')),
        ('other', _('Other')),
    ]

    GENRE_CHOICES = [
        ('action', _('Action')),
        ('drama', _('Drama')),
        ('comedy', _('Comedy')),
        ('thriller', _('Thriller')),
        ('romance', _('Romance')),
        ('sci-fi', _('Sci-Fi')),
        ('horror', _('Horror')),
        ('fantasy', _('Fantasy')),
        ('animation', _('Animation')),
        ('adventure', _('Adventure')),
        ('crime', _('Crime')),
        ('mystery', _('Mystery')),
        ('family', _('Family')),
        ('history', _('History')),
        ('music', _('Music')),
        ('war', _('War')),
        ('western', _('Western')),
        ('biography', _('Biography')),
        ('sport', _('Sport')),
        ('other', _('Other')),
    ]

    LANGUAGE_CHOICES = [
        ('am', _('Amharic')),
        ('en', _('English')),
        ('om', _('Afaan Oromo')),
        ('ti', _('Tigrinya')),
        ('so', _('Somali')),
        ('ar', _('Arabic')),
        ('fr', _('French')),
        ('es', _('Spanish')),
        ('hi', _('Hindi')),
        ('other', _('Other')),
    ]

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"))

    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='movie'
    )
    genre = models.CharField(
        _("Genre"),
        max_length=30,
        choices=GENRE_CHOICES,
        default='other'
    )
    language = models.CharField(
        _("Language"),
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default='en'
    )

    thumbnail = models.ImageField(_("Thumbnail"), upload_to='thumbnails/')
    video_file = models.FileField(
        _("Upload Video"),
        upload_to='secure_videos/',
        blank=True,
        null=True,
        validators=[validate_video_extension],
        help_text=_("Upload video securely")
    )
    video_url = models.URLField(
        _("Video URL"),
        blank=True,
        null=True,
        help_text=_("Optional external video URL")
    )
    hls_folder = models.CharField(
        _("HLS Folder"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Path to generated HLS folder")
    )

    price_per_view = models.DecimalField(
        _("Price per View"),
        max_digits=8,
        decimal_places=2,
        default=0.00
    )
    duration_minutes = models.PositiveIntegerField(
        _("Duration (minutes)"),
        help_text=_("Total duration in minutes")
    )
    release_date = models.DateField(_("Release Date"))
    created_at = models.DateTimeField(auto_now_add=True)

    # Analytics
    total_plays = models.PositiveIntegerField(_("Total Plays"), default=0)
    unique_viewers = models.PositiveIntegerField(_("Unique Viewers"), default=0)
    total_watch_time_seconds = models.PositiveIntegerField(_("Total Watch Time (seconds)"),
        default=0
    )
    completion_rate = models.DecimalField(
        _("Completion Rate"),
        max_digits=5,
        decimal_places=2,
        default=0.00
    )
    average_rating = models.FloatField(_("Average Rating"), default=0.0)
    total_ratings = models.PositiveIntegerField(_("Total Ratings"), default=0)

    def str(self):
        return self.title


# ------------------- HLS Conversion Signal -------------------
@receiver(post_save, sender=StreamingContent)
def convert_video_to_hls_signal(sender, instance, created, **kwargs):
    """
    Automatically convert uploaded videos to HLS if not already converted.
    """
    if instance.video_file and not instance.hls_folder:
        try:
            video_path = instance.video_file.path
            output_dir = os.path.join(settings.MEDIA_ROOT, 'hls')
            hls_folder, _ = convert_video_to_hls(
                video_path=video_path,
                output_dir=output_dir,
                content_id=instance.id,
                verbose=True
            )
            instance.hls_folder = os.path.relpath(hls_folder, settings.MEDIA_ROOT).replace("\\", "/")
            instance.save(update_fields=['hls_folder'])
        except Exception as e:
            print("⚠️ HLS conversion failed:", e)



# -------------------- Stream View Log --------------------
class StreamViewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(StreamingContent, on_delete=models.CASCADE)
    views = models.IntegerField(_("Views"), default=0)
    last_viewed = models.DateTimeField(_("Last Viewed"), auto_now=True)
    watch_time_seconds = models.PositiveIntegerField(_("Watch Time (seconds)"), default=0)
    country = CountryField(_("Country"), blank=True, null=True)

    class Meta:
        unique_together = ('user', 'content')

    def str(self):
        return f"{self.user.username} - {self.content.title}"


# -------------------- User Profile --------------------
def profile_image_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"profile_{instance.user.id}.{ext}"
    return os.path.join('profile_pics', filename)


from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

def profile_image_path(instance, filename):
    return f'profiles/{instance.user.username}/{filename}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(
        _("Profile Picture"), 
        upload_to=profile_image_path, 
        default='profile_pics/default_profile.png'
    )
    bio = models.TextField(_("Bio"), blank=True, null=True)
    history_cleared_at = models.DateTimeField(_("History Cleared At"), blank=True, null=True)  # ✅ track last clear

    def str(self):
        return self.user.username


# -------------------- Watch History --------------------
class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video_title = models.CharField(_("Video Title"), max_length=255)
    watch_date = models.DateTimeField(_("Watch Date"), default=timezone.now)
    duration_watched = models.PositiveIntegerField(_("Duration Watched (minutes)"), default=0)

    def str(self):
        return f"{self.user.username} - {self.video_title}"


# -------------------- Streaming Analytics --------------------


# models.py
from django.db import models
from django.contrib.auth.models import User

class StreamingRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey('StreamingContent', on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField()  # 1-5
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'content')  # One rating per user per video
