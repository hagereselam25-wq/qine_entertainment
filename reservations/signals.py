from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from .models import Movie, Seat

@receiver(post_save, sender=Movie)
def create_custom_seats(sender, instance, created, **kwargs):
    if created:
        for row_num in range(instance.num_rows):
            row_letter = chr(65 + row_num)  # 'A', 'B', 'C'...
            for seat_num in range(1, instance.seats_per_row + 1):
                # Seat label format translatable if needed
                seat_label = _(f"{row_letter}{seat_num}")  
                Seat.objects.create(
                    movie=instance,
                    seat_number=seat_label,
                    is_booked=False
                )