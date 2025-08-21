from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render
import csv
from django.utils.translation import gettext_lazy as _

from .models import StreamingContent, StreamingSubscription, StreamViewLog, StreamingAnalytics

# ------------------- Streaming Content Admin ------------------- 
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.http import HttpResponse
import csv
from django.db.models import Sum
from .models import StreamingContent, StreamViewLog

@admin.register(StreamingContent)
class StreamingContentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'total_plays', 'unique_viewers',
        'average_rating',  # <-- Added Average Rating column
        'total_watch_time_minutes_display', 'completion_rate', 'release_date',
        'hls_folder', 'download_analytics_csv'
    )
    search_fields = ('title',)
    list_filter = ('category', 'release_date')
    ordering = ('-release_date',)
    readonly_fields = ('hls_folder', 'total_watch_time_minutes_display', 'average_rating')

    def total_watch_time_minutes_display(self, obj):
        total_seconds = StreamViewLog.objects.filter(content=obj).aggregate(
            total=Sum('watch_time_seconds')
        )['total'] or 0
        return total_seconds // 60
    total_watch_time_minutes_display.short_description = _('Total Watch Time (min)')

    def download_analytics_csv(self, obj):
        return format_html(
            '<a class="button" href="/admin/streaming/streamingcontent/{}/download_csv/">{}</a>',
            obj.id,
            _('Download CSV')
        )
    download_analytics_csv.short_description = _('Analytics CSV')

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
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{content.title}_analytics.csv"'
        writer = csv.writer(response)

        # ✅ Write aggregated headers
        writer.writerow([
            _('Title'),
            _('Category'),
            _('Total Plays'),
            _('Unique Viewers'),
            _('Average Rating'),
            _('Total Watch Time (min)'),
            _('Completion Rate'),
            _('Release Date')
        ])

        # ✅ Write single aggregated row from StreamingContent
        total_watch_time_minutes = StreamViewLog.objects.filter(content=content).aggregate(
            total=Sum('watch_time_seconds')
        )['total'] or 0

        writer.writerow([
            content.title,
            content.category,
            content.total_plays,
            content.unique_viewers,
            round(content.average_rating or 0, 2),
            total_watch_time_minutes // 60,
            f"{content.completion_rate:.2f}",
            content.release_date.strftime('%Y-%m-%d') if content.release_date else ''
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
        return _("No QR code")
    qr_preview.short_description = _("QR Code")

# ------------------- Stream View Log Admin -------------------
@admin.register(StreamViewLog)
class StreamViewLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'views', 'watch_time_minutes_display', 'last_viewed', 'country_display')
    list_filter = ('last_viewed',)
    search_fields = ('userusername', 'contenttitle')

    def watch_time_minutes_display(self, obj):
        return (obj.watch_time_seconds or 0) // 60
    watch_time_minutes_display.short_description = _('Watch Time (min)')

    def country_display(self, obj):
        return obj.country.name if obj.country else _('Unknown')
    country_display.short_description = _('Country')

# ------------------- Streaming Analytics Admin -------------------
from django.contrib import admin
from django.shortcuts import render
from django.db.models import Sum, Count, Avg
from django.utils.translation import gettext_lazy as _

from .models import StreamingAnalytics, StreamViewLog, StreamingContent, StreamingRating

@admin.register(StreamingAnalytics)
class StreamingAnalyticsAdmin(admin.ModelAdmin):
    change_list_template = "admin/streaming/analytics.html"  # Your template

    def has_module_permission(self, request):
        return True  # Show in Streaming section

    def changelist_view(self, request, extra_context=None):
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
            country = item['country'] or _('Unknown')
            percent = round(item['count'] / total_region_count * 100, 2)
            top_regions[country] = percent

        # ------------------------
        # Rating Analytics
        # ------------------------
        rating_data = StreamingContent.objects.annotate(
            avg_rating=Avg('ratings__rating'),
            total_ratings=Count('ratings')
        ).order_by('-avg_rating')[:10]  # top 10 by avg_rating

        ratings_stats = []
        for content in rating_data:
            ratings_stats.append({
                'title': content.title,
                'avg_rating': round(content.avg_rating or 0, 2),
                'total_ratings': content.total_ratings,
            })

        stats = {
            'total_views': total_views,
            'unique_viewers': unique_viewers,
            'total_watch_time_hours': round(total_watch_time_seconds / 3600, 2),
            'avg_watch_time_per_view_minutes': round(avg_watch_time_per_view / 60, 2),
            'top_regions': top_regions,
            'ratings_stats': ratings_stats,  # Add rating analytics
        }

        extra_context = extra_context or {}
        extra_context.update({'stats': stats})
        return render(request, "admin/streaming/analytics.html", extra_context)
