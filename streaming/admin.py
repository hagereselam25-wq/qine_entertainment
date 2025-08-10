from django.contrib import admin
from django.utils.html import format_html
from .models import StreamingContent, StreamingSubscription, StreamViewLog

@admin.register(StreamingContent)
class StreamingContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'release_date', 'duration_minutes')
    search_fields = ('title',)
    list_filter = ('category', 'release_date')
    ordering = ('-release_date',)

@admin.register(StreamingSubscription)
class StreamingSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'subscription_type', 'amount', 'is_paid', 'access_expires_at')
    list_filter = ('subscription_type', 'is_paid', 'created_at')
    search_fields = ('full_name', 'email', 'chapa_tx_ref')
    readonly_fields = ('qr_preview', 'access_expires_at')
    ordering = ('-created_at',)

    def qr_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="150" height="150" />', obj.qr_code.url)
        return "No QR code"
    qr_preview.short_description = "QR Code"

@admin.register(StreamViewLog)
class StreamViewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'views', 'last_viewed')
    list_filter = ('last_viewed',)
    search_fields = ('user__username', 'content__title')
