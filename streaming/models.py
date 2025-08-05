from django.db import models
from django.contrib.auth.models import User

class MediaContent(models.Model):
    CATEGORY_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Horror', 'Horror'),
        ('Romance', 'Romance'),
        ('Sci-Fi', 'Sci-Fi'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    video_file = models.FileField(upload_to='media_videos/', blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return 0


class MediaRating(models.Model):
    media = models.ForeignKey(MediaContent, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('media', 'user')

    def __str__(self):
        return f"{self.user.username} rated {self.media.title} - {self.rating}"

from django.db import models

class StreamingContent(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_url = models.URLField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class VideoRating(models.Model):
    content = models.ForeignKey(StreamingContent, on_delete=models.CASCADE, related_name='ratings', null=True, blank=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=0)
    comment = models.TextField(blank=True, null=True)
    rated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} rated {self.content.title} - {self.rating}"
