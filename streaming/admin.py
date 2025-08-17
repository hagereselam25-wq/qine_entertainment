from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render
import csv

from .models import StreamingContent, StreamingSubscription, StreamViewLog

# ------------------- Streaming Content Admin -------------------
@admin.register(StreamingContent)
class StreamingContentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'total_plays',
        'unique_viewers',
        'total_watch_time_minutes_display',
        'completion_rate',
        'release_date',
        'hls_folder',
        'download_analytics_csv'
    )
    search_fields = ('title',)
    list_filter = ('category', 'release_date')
    ordering = ('-release_date',)
    readonly_fields = ('hls_folder', 'total_watch_time_minutes_display')

    def total_watch_time_minutes_display(self, obj):
        total_seconds = StreamViewLog.objects.filter(content=obj).aggregate(
            total=Sum('watch_time_seconds')
        )['total'] or 0
        return total_seconds // 60
    total_watch_time_minutes_display.short_description = 'Total Watch Time (min)'

    def download_analytics_csv(self, obj):
        return format_html(
            '<a class="button" href="/admin/streaming/streamingcontent/{}/download_csv/">Download CSV</a>',
            obj.id
        )
    download_analytics_csv.short_description = 'Analytics CSV'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:content_id>/download_csv/',
                 self.admin_site.admin_view(self.download_csv_view),
                 name='streamingcontent_download_csv')
        ]
        return custom_urls + urls

    def download_csv_view(self, request, content_id):
        content = self.get_object(request, content_id)
        logs = StreamViewLog.objects.filter(content=content)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{content.title}_analytics.csv"'
        writer = csv.writer(response)
        writer.writerow(['User', 'Views', 'Watch Time (min)', 'Completion Rate', 'Country'])
        for log in logs:
            writer.writerow([
                log.user.username,
                log.views,
                (log.watch_time_seconds or 0) // 60,
                log.content.completion_rate,
                log.country.name if log.country else 'Unknown'
            ])
        return response

# -------------------- Streaming Subscription Admin --------------------
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

# ------------------- Stream View Log Admin -------------------
@admin.register(StreamViewLog)
class StreamViewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'views', 'watch_time_minutes_display', 'last_viewed', 'country_display')
    list_filter = ('last_viewed',)
    search_fields = ('userusername', 'contenttitle')

    def watch_time_minutes_display(self, obj):
        return (obj.watch_time_seconds or 0) // 60
    watch_time_minutes_display.short_description = 'Watch Time (min)'

    def country_display(self, obj):
        return obj.country.name if obj.country else 'Unknown'
    country_display.short_description = 'Country'

# ------------------- Custom Analytics View -------------------
def streaming_analytics_view(request):
    logs = StreamViewLog.objects.all()
    total_views = logs.aggregate(total=Sum('views'))['total'] or 0
    unique_viewers = logs.values('user').distinct().count()
    total_watch_time_seconds = logs.aggregate(total=Sum('watch_time_seconds'))['total'] or 0
    avg_watch_time_per_view = (total_watch_time_seconds / total_views) if total_views else 0

    # Top regions
    top_regions = {}
    region_data = logs.values('country').annotate(count=Count('id')).order_by('-count')[:5]
    total_region_count = sum(item['count'] for item in region_data) or 1
    for item in region_data:
        country = item['country'] or 'Unknown'
        percent = round(item['count'] / total_region_count * 100, 2)
        top_regions[country] = percent

    stats = {
        'total_views': total_views,
        'unique_viewers': unique_viewers,
        'total_watch_time_hours': round(total_watch_time_seconds / 3600, 2),
        'avg_watch_time_per_view_minutes': round(avg_watch_time_per_view / 60, 2),
        'top_regions': top_regions
    }

    context = dict(
        admin.site.each_context(request),
        stats=stats
    )
    return render(request, "admin/streaming/analytics.html", context)

# ------------------- Add custom URL to admin safely -------------------
def get_admin_urls(original_urls):
    custom_urls = [
        path('streaming/analytics/', admin.site.admin_view(streaming_analytics_view), name='streaming_analytics'),
    ]
    return custom_urls + original_urls

original_get_urls = admin.site.get_urls
admin.site.get_urls = lambda: get_admin_urls(original_get_urls())