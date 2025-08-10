from django.urls import path
from .views import verify_subscription_payment, subscription_thankyou
from .views import create_subscription
from django.urls import path
from django.urls import path
from . import views 
from .views import user_login, user_logout, user_signup


app_name = 'streaming'

urlpatterns = [
    # Payment and subscription
    path('subscribe/', views.create_subscription, name='create_subscription'),
    path('verify/', views.verify_subscription_payment, name='verify_subscription_payment'),
    path('thankyou/', views.subscription_thankyou, name='subscription_thankyou'),

    # Auth
    path('signup/', views.user_signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),

]


