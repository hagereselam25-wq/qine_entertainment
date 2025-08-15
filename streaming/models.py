from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django_countries.fields import CountryField
import os

SUBSCRIPTION_CHOICES = (
    ('monthly', 'Monthly'),
    ('annual', 'Annual'),
)

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tx_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.tx_ref} - {self.status}"


class StreamingSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES)
    chapa_tx_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    access_expires_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def has_access(self):
        return self.is_paid and self.access_expires_at and timezone.now() < self.access_expires_at

    def __str__(self):
        return f"{self.full_name} - {self.subscription_type}"


class StreamingContent(models.Model):
    CATEGORY_CHOICES = [
        ('movie', 'Movie'),
        ('series', 'Series'),
        ('documentary', 'Documentary'),
        ('short', 'Short Film'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='movie')
    thumbnail = models.ImageField(upload_to='thumbnails/')
    video_file = models.FileField(upload_to='secure_videos/', blank=True, null=True,
                                  help_text="Upload video securely")
    video_url = models.URLField(blank=True, null=True, help_text="Optional external video URL")
    price_per_view = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    duration_minutes = models.PositiveIntegerField(help_text="Total duration in minutes")
    release_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Analytics
    total_plays = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    total_watch_time_minutes = models.PositiveIntegerField(default=0)  # Total watch time in minutes
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # % value

    def __str__(self):
        return self.title

    def average_watch_time(self):
        return (self.total_watch_time_minutes / self.total_plays) if self.total_plays else 0


class StreamViewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(StreamingContent, on_delete=models.CASCADE)
    views = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(auto_now=True)
    watch_time_minutes = models.PositiveIntegerField(default=0)
    country = CountryField(blank=True, null=True)  # Track user region

    def __str__(self):
        return f"{self.user.username} - {self.content.title}"

    class Meta:
        unique_together = ('user', 'content')  # One log per user per content

def profile_image_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"profile_{instance.user.id}.{ext}"
    return os.path.join('profile_pics', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(
        upload_to=profile_image_path,
        default='profile_pics/default_profile.png'
    )
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.username


class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video_title = models.CharField(max_length=255)
    watch_date = models.DateTimeField(default=timezone.now)
    duration_watched = models.PositiveIntegerField(default=0)  # in minutes

    def __str__(self):
        return f"{self.user.username} - {self.video_title}"
