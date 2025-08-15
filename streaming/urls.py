from django.urls import path
from .views import verify_subscription_payment, subscription_thankyou
from .views import create_subscription
from django.urls import path
from django.urls import path
from . import views 
from .views import stream_video, user_profile

app_name = 'streaming'

urlpatterns = [
    # Payment and subscription
    path('subscribe/', views.create_subscription, name='create_subscription'),
    path('verify/', views.verify_subscription_payment, name='verify_subscription_payment'),
    path('thankyou/', views.subscription_thankyou, name='subscription_thankyou'),
    path('', views.streaming_home, name='streaming_home'),
    path('watch/<int:content_id>/', views.watch_video, name='watch_video'),
    path('stream/', stream_video, name='stream_video'),
    path('watch/<int:content_id>/report/', views.report_watch_time, name='report_watch_time'),
    # Auth
    path('signup/', views.user_signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', user_profile, name='user_profile'),

]


