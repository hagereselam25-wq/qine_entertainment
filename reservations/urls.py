# our urls.py maps URLs to views — tells Django which function to run when a user visits a certain URL
from django.urls import path
from . import views

# our path defines 'url-pattern/' → the URL users type or click. views.view_function → the function that handles the request. name='route_name' → a unique identifier for reverse URL lookup (useful in templates and redirects).
urlpatterns = [
    path('', views.home, name='home'),
    path('movie/<int:movie_id>/seats/', views.seat_selection, name='seat_selection'),
    path('ticket/<int:ticket_id>/', views.ticket_confirmation, name='ticket_confirmation'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),

    # Admin URLs
   

    path("about/", views.about_view, name="about"),
    path("contact/", views.contact_view, name="contact"),
    path("cinema/", views.cinema, name="cinema"),

]
