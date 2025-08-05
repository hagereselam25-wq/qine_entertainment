from django.contrib import admin
from .models import Movie, Seat, Reservation, Booking, Rating


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'show_time')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'movie', 'seat', 'reservation_time']
    list_filter = ['movie', 'reservation_time']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['movie', 'seat', 'user_name']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['movie', 'rating']
