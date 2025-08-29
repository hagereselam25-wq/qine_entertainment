from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views import verify_subscription_payment, subscription_thankyou, create_subscription, user_profile

app_name = 'streaming'

urlpatterns = [
    # Payment and subscription
    path('subscribe/', create_subscription, name='create_subscription'),
    path('verify/', verify_subscription_payment, name='verify_subscription_payment'),
    path('thankyou/', subscription_thankyou, name='subscription_thankyou'),

    # Streaming
    path('', views.streaming_home, name='streaming_home'),
    path('watch/<int:content_id>/', views.watch_video, name='watch_video'),
    path('watch/<int:content_id>/report/', views.report_watch_time, name='report_watch_time'),
    path('profile/', views.user_profile, name='user_profile'),
    path('clear-watch-history/', views.clear_watch_history, name='clear_watch_history'),

    # Authentication
    path('signup/', views.user_signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', user_profile, name='user_profile'),
    path('profile/clear-history/', views.clear_watch_history, name='clear_watch_history'),
   
    # Password reset (custom templates inside streaming/)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="streaming/password_reset_form.html",
            email_template_name="streaming/password_reset_email.html",
            subject_template_name="streaming/password_reset_subject.txt",
            success_url="/streaming/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="streaming/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="streaming/password_reset_confirm.html",
            success_url="/streaming/reset/done/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="streaming/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # i18n
    path('i18n/', include('django.conf.urls.i18n')),

    # Rating
    path('rate/<int:content_id>/', views.rate_video, name='rate_video'),

    # Analytics
    path('admin/streaming/streaminganalytics/', views.streaming_analytics, name='streaming_analytics'),
    path('admin/streaming/streaminganalytics/export_csv/', views.export_analytics_csv, name='export_analytics_csv'),
    path("analytics/", views.streaming_analytics, name="analytics"),
    path("analytics/download/", views.export_analytics_csv, name="export_analytics_csv"),

    # Temporary endpoint (REMOVE after use)
    path('create-superuser/', views.create_superuser_view, name='create_superuser'),

]