from django.contrib import admin
from .models import Movie, Reservation, Transaction

# this are basically our db models being registered on our django admin panel
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'show_time') #this are our columns 

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'movie', 'seat', 'reservation_time']
    list_filter = ['movie', 'reservation_time']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'transaction_id', 'amount', 'status', 'created_at']
