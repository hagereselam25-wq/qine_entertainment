from django.urls import path
from . import views

app_name = 'streaming'

urlpatterns = [
    path('', views.media_list, name='media_list'),
    path('<int:pk>/', views.media_detail, name='media_detail'),
]
