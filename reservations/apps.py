# our app helps django to initialize our reservation app defining custom configs
from django.apps import AppConfig

class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'

    def ready(self):
        import reservations.signals  # imports the signals to ensure they are connected
