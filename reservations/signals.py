# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Movie, Seat

@receiver(post_save, sender=Movie)
def create_custom_seats(sender, instance, created, **kwargs):
    if created:
        for row_num in range(instance.num_rows):  # Creates rows A, B, C, etc.
            row_letter = chr(65 + row_num)  # 'A', 'B', 'C'...
            for seat_num in range(1, instance.seats_per_row + 1):  # Creates 1, 2, 3... for each row
                seat_label = f"{row_letter}{seat_num}"  # Seat format e.g., A1, A2, B1
                Seat.objects.create(
                    movie=instance,
                    seat_number=seat_label,
                    is_booked=False
                )
