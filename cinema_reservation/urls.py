# cinema_reservation/urls.py

from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static  # ✅ Serve media files in development

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reservations.urls')),  # Your reservation app routes
    path('streaming/', include('streaming.urls', namespace='streaming')),  # Streaming app routes
]

# Serve media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve static files during development if DEBUG=True
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
