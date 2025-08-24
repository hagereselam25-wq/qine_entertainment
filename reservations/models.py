from django.db import models
from django.utils.translation import gettext_lazy as _


class Movie(models.Model):
    title = models.CharField(_("Title"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    show_time = models.DateTimeField(_("Show Time"))

    poster = models.ImageField(_("Poster"), upload_to='posters/', blank=True, null=True)
    trailer_file = models.FileField(_("Trailer File"), upload_to='trailers/', blank=True, null=True)
    trailer_url = models.URLField(_("Trailer URL"), blank=True, null=True)

    num_rows = models.PositiveIntegerField(_("Number of Rows"), default=5)
    seats_per_row = models.PositiveIntegerField(_("Seats per Row"), default=10)

    rating = models.PositiveIntegerField(_("Rating"), default=0)

    ticket_price = models.DecimalField(_("Ticket Price (ETB)"), max_digits=8, decimal_places=2, default=50.00)

    def str(self):
        return self.title


class Seat(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name=_("Movie"))
    seat_number = models.CharField(_("Seat Number"), max_length=5)
    is_booked = models.BooleanField(_("Is Booked"), default=False)

    def __str__(self):
        return f"{self.movie.title} - {self.seat_number}"


class Reservation(models.Model):
    user = models.CharField(_("User"), max_length=100)
    email = models.EmailField(_("Email"), default="default@example.com")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name=_("Movie"))
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, verbose_name=_("Seat"))
    reservation_time = models.DateTimeField(_("Reservation Time"), auto_now_add=True)
    qr_code = models.ImageField(_("QR Code"), upload_to='qrcodes/', blank=True)
    is_paid = models.BooleanField(_("Is Paid"), default=False)
    email_sent = models.BooleanField(_("Email Sent"), default=False)

    def __str__(self):
        return f"{self.user} - {self.movie.title} - {self.seat.seat_number}"


class Transaction(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, verbose_name=_("Reservation"))
    transaction_id = models.CharField(_("Transaction ID"), max_length=100)
    amount = models.DecimalField(_("Amount"), max_digits=8, decimal_places=2)
    status = models.CharField(_("Status"), max_length=20)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"


class Rating(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='ratings', verbose_name=_("Movie"))
    rating = models.IntegerField(_("Rating"))

    def __str__(self):
        return f'{self.movie.title} - {self.rating}'
