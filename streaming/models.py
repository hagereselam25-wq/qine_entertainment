from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # or ForeignKey if multiple subs per user
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES)
    chapa_tx_ref = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # <--- Make sure this exists
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
    video_url = models.URLField(help_text="Paste the direct video URL or embed link")
    duration_minutes = models.PositiveIntegerField(help_text="Total duration in minutes")
    release_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class StreamViewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(StreamingContent, on_delete=models.CASCADE)
    views = models.IntegerField(default=0)
    last_viewed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.content.title}"
