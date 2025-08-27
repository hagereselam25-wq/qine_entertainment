from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
import csv

from .models import StreamingContent, StreamingSubscription, StreamViewLog, StreamingAnalyticsProxy


from django.db.models import Sum, Count, F
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
import csv

from .models import StreamingContent, StreamingSubscription, StreamViewLog


@admin.register(StreamingContent)
class StreamingContentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'total_plays', 'unique_viewers',
        'average_rating',
        'total_watch_time_minutes_display', 'completion_rate', 'release_date',
        'hls_folder', 'download_analytics_csv'
    )
    search_fields = ('title',)
    list_filter = ('category', 'release_date')
    ordering = ('-release_date',)
    readonly_fields = ('hls_folder', 'total_watch_time_minutes_display', 'average_rating')

    # -------------------- Existing Methods --------------------
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

    # -------------------- Custom URLs --------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:content_id>/download_csv/',
                 self.admin_site.admin_view(self.download_csv_view),
                 name='streamingcontent_download_csv'),
            path('analytics/',  # New analytics page
                 self.admin_site.admin_view(self.analytics_view),
                 name='streamingcontent_analytics'),
        ]
        return custom_urls + urls

    # -------------------- CSV Download --------------------
    def download_csv_view(self, request, content_id):
        content = self.get_object(request, content_id)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{content.title}_analytics.csv"'
        writer = csv.writer(response)

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

    # -------------------- Analytics Page --------------------
    def analytics_view(self, request):
        content_stats = (
            StreamViewLog.objects
            .values('content__title')
            .annotate(
                total_views=Sum('views'),
                unique_viewers=Count('user', distinct=True),
                total_watch_time=Sum('watch_time_seconds')
            )
            .order_by('-total_views')
        )

        # Prepare data for Chart.js
        labels = [c['content__title'] for c in content_stats]
        total_views_data = [c['total_views'] for c in content_stats]
        unique_viewers_data = [c['unique_viewers'] for c in content_stats]
        context = {
            'content_stats': content_stats,
            'labels': labels,
            'total_views_data': total_views_data,
            'unique_viewers_data': unique_viewers_data,
        }
        return render(request, 'admin/streaming_analytics.html', context)

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

from django.contrib import admin
from .models import StreamingContent, StreamingRating

@admin.register(StreamingRating)
class StreamingRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'rating')
    list_filter = ('rating',)
    search_fields = ('userusername', 'contenttitle')
   
   
   
# streaming/admin.py# streaming/admin.py
from django.contrib import admin
from django.db.models import Sum, Count, F, Avg
from .models import StreamViewLog, StreamingAnalyticsProxy, StreamingContent

@admin.register(StreamingAnalyticsProxy)
class StreamingAnalyticsProxyAdmin(admin.ModelAdmin):
    change_list_template = "admin/streaming/analytics_chart.html"
    list_display = ()  # Hide table, show charts only

    def changelist_view(self, request, extra_context=None):
        # Aggregate from StreamViewLog joined with StreamingContent
        qs = StreamViewLog.objects.values(
            "content__title",
            "content__category",
            "content__genre",
            "content__language",
        ).annotate(
            total_views=Sum("views"),
            unique_users=Count("user", distinct=True),
            total_watch_time_seconds=Sum("watch_time_seconds"),
            content_duration=F("content__duration_minutes"),
            avg_rating=Avg("content__average_rating"),
        ).order_by("-total_views")

        labels = [item["content__title"] for item in qs]
        views = [item["total_views"] or 0 for item in qs]
        unique_users = [item["unique_users"] or 0 for item in qs]
        ratings = [round(item["avg_rating"] or 0, 2) for item in qs]

        # Calculate completion rates
        completion_rates = []
        for item in qs:
            duration_minutes = item["content_duration"] or 0
            duration_seconds = duration_minutes * 60

            if duration_seconds > 0 and item["total_views"]:
                avg_watch = (item["total_watch_time_seconds"] or 0) / item["total_views"]
                completion_rate = min(avg_watch / duration_seconds, 1) * 100
            else:
                completion_rate = 0

            completion_rates.append(round(completion_rate, 2))

        # Global KPIs
        total_views = sum(views)
        avg_completion_rate = round(sum(completion_rates) / len(completion_rates), 2) if completion_rates else 0
        total_unique_users = sum(unique_users)
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0

        # Category distribution
        category_qs = StreamingContent.objects.values("category").annotate(count=Count("id"))
        categories = [c["category"] for c in category_qs]
        category_counts = [c["count"] for c in category_qs]

        # Genre distribution
        genre_qs = StreamingContent.objects.values("genre").annotate(count=Count("id"))
        genres = [g["genre"] for g in genre_qs]
        genre_counts = [g["count"] for g in genre_qs]

        # Language distribution
        lang_qs = StreamingContent.objects.values("language").annotate(count=Count("id"))
        languages = [l["language"] for l in lang_qs]
        language_counts = [l["count"] for l in lang_qs]

        # Country views (from logs)
        country_qs = StreamViewLog.objects.values("country").annotate(total=Sum("views"))
        countries = [c["country"] or "Unknown" for c in country_qs]
        country_views = [c["total"] for c in country_qs]

        extra_context = extra_context or {}
        extra_context.update({
            # Per-content
            "labels": labels,
            "views": views,
            "unique_users": unique_users,
            "completion_rates": completion_rates,
            "ratings": ratings,

            # Global KPIs
            "total_views": total_views,
            "avg_completion_rate": avg_completion_rate,
            "total_unique_users": total_unique_users,
            "avg_rating": avg_rating,

            # Distributions
            "categories": categories,
            "category_counts": category_counts,
            "genres": genres,
            "genre_counts": genre_counts,
            "languages": languages,
            "language_counts": language_counts,
            "countries": countries,
            "country_views": country_views,
        })

        return super().changelist_view(request, extra_context=extra_context)