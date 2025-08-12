from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from .models import StreamingContent, StreamingSubscription, StreamViewLog
from django.db import models

class StreamingAnalytics(models.Model):
    class Meta:
        managed = False
        verbose_name = "Streaming Analytics"
        verbose_name_plural = "Streaming Analytics"


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

class StreamingAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = "admin/streaming/analytics.html"
    
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        logs = StreamViewLog.objects.all()

        total_views = logs.aggregate(total=Sum('views'))['total'] or 0
        unique_viewers = logs.values('user').distinct().count()

        # Assuming you have watch_time_minutes in model, else 0
        if 'watch_time_minutes' in [f.name for f in StreamViewLog._meta.get_fields()]:
            total_watch_time = logs.aggregate(total=Sum('watch_time_minutes'))['total'] or 0
        else:
            total_watch_time = 0
        
        avg_watch_time_per_view = (total_watch_time / total_views) if total_views else 0

        completion_rate = 72.0  # Placeholder fixed value
        
        # Calculate top regions with percentages if 'country' exists
        top_regions = {}
        if 'country' in [f.name for f in StreamViewLog._meta.get_fields()]:
            region_data = logs.values('country').annotate(count=Count('id')).order_by('-count')[:5]
            total_region_count = sum(item['count'] for item in region_data) or 1
            for item in region_data:
                country = item['country'] or 'Unknown'
                percent = round(item['count'] / total_region_count * 100, 2)
                top_regions[country] = percent

        stats = {
            'total_views': total_views,
            'unique_viewers': unique_viewers,
            'total_watch_time_hours': round(total_watch_time / 60, 2),
            'avg_watch_time_per_view': round(avg_watch_time_per_view / 60, 2),  # convert mins to hours
            'completion_rate': completion_rate,
            'top_regions': top_regions,
        }

        extra_context = extra_context or {}
        extra_context.update({'stats': stats})

        return super().changelist_view(request, extra_context=extra_context)

# Register dummy model for Analytics page
from django.apps import apps
DummyModel = type('StreamingAnalytics', (object,), {'__module__': ''})
admin.site.register(StreamingAnalytics, StreamingAnalyticsAdmin)
