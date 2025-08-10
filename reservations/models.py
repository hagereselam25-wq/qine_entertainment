from django.db import models

class Movie(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    show_time = models.DateTimeField()
    
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    trailer = models.FileField(upload_to='trailers/', blank=True, null=True)

    num_rows = models.PositiveIntegerField(default=5)
    seats_per_row = models.PositiveIntegerField(default=10)

    is_streaming = models.BooleanField(default=False)
    stream_url = models.URLField(blank=True, null=True)

    trailer_file = models.FileField(upload_to='trailers/', blank=True, null=True)
    trailer_url = models.URLField(blank=True, null=True)

    rating = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

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
    is_paid = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.movie.title} - {self.seat.seat_number}"

class Transaction(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"

class Rating(models.Model):
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField()

    def __str__(self):
        return f'{self.movie.title} - {self.rating}'
