from django.contrib import admin
from .models import Movie, Seat, Reservation, Rating, Transaction

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'show_time')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'movie', 'seat', 'reservation_time']
    list_filter = ['movie', 'reservation_time']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['movie', 'rating']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'transaction_id', 'amount', 'status', 'created_at']
