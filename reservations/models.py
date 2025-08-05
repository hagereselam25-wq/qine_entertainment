# models.py
from django.db import models
from django.contrib.auth.models import User

class Movie(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    show_time = models.DateTimeField()
    
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    trailer = models.FileField(upload_to='trailers/', blank=True, null=True)  # Can be URLField if using external links

    def __str__(self):
        return self.title

    # Seating layout
    num_rows = models.PositiveIntegerField(default=5)
    seats_per_row = models.PositiveIntegerField(default=10)

    # Streaming details
    is_streaming = models.BooleanField(default=False)
    stream_url = models.URLField(blank=True, null=True)

    # Movie teaser/trailer
    trailer_file = models.FileField(upload_to='trailers/', blank=True, null=True)
    trailer_url = models.URLField(blank=True, null=True)

    # Admin-defined rating
    rating = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title



# Optional Rating Model for user-generated ratings
class Rating(models.Model):
    movie = models.ForeignKey(
        'Movie', 
        on_delete=models.CASCADE, 
        related_name='ratings'  # Add this line to avoid the reverse conflict
    )
    rating = models.IntegerField()

    def __str__(self):
        return f'{self.movie.title} - {self.rating}'


class Seat(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=5)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.movie.title} - {self.seat_number}"

class Reservation(models.Model):
    user = models.CharField(max_length=100)
    email = models.EmailField(default="default@example.com")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE)
    reservation_time = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True)

    def __str__(self):
        return f"{self.user} - {self.movie.title} - {self.seat.seat_number}"

class Booking(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True)

    def __str__(self):
        return f"{self.user_name} - {self.seat.seat_number}"
