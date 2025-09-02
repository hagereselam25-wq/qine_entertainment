from django.contrib.admin import AdminSite
from django.contrib import admin
from django.db.models import Sum, Count, F, Avg
from django.utils.html import format_html
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
import csv


# cinema_reservation/admin.py (project-level)

from django.contrib.admin import AdminSite
from django.contrib import admin
from reservations.admin import MovieAdmin, ReservationAdmin, TransactionAdmin
from reservations.models import Movie, Reservation, Transaction
from streaming.admin import (
    StreamingContentAdmin, StreamingSubscriptionAdmin, 
    StreamViewLogAdmin, StreamingRatingAdmin, StreamingAnalyticsProxyAdmin
)
from streaming.models import (
    StreamingContent, StreamingSubscription, StreamViewLog, 
    StreamingRating, StreamingAnalyticsProxy
)

# ------------------- Custom Admin Site -------------------
admin_site = AdminSite(name='custom_admin')
admin_site.site_header = "Qine Cinema Admin"
admin_site.site_title = "Qine Portal"
admin_site.index_title = "Admin Dashboard"

# ------------------- Register Reservation Models -------------------
admin_site.register(Movie, MovieAdmin)
admin_site.register(Reservation, ReservationAdmin)
admin_site.register(Transaction, TransactionAdmin)

# ------------------- Register Streaming Models -------------------
admin_site.register(StreamingContent, StreamingContentAdmin)
admin_site.register(StreamingSubscription, StreamingSubscriptionAdmin)
admin_site.register(StreamViewLog, StreamViewLogAdmin)
admin_site.register(StreamingRating, StreamingRatingAdmin)
admin_site.register(StreamingAnalyticsProxy, StreamingAnalyticsProxyAdmin)


# -------------------- Reservations --------------------
from reservations.models import Movie, Reservation, Transaction

@admin.register(Movie, site=admin_site)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'show_time')

@admin.register(Reservation, site=admin_site)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'movie', 'seat', 'reservation_time']
    list_filter = ['movie', 'reservation_time']

@admin.register(Transaction, site=admin_site)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'transaction_id', 'amount', 'status', 'created_at']

# -------------------- Streaming --------------------
from streaming.models import (
    StreamingContent,
    StreamingSubscription,
    StreamViewLog,
    StreamingAnalyticsProxy,
    StreamingRating
)

@admin.register(StreamingContent, site=admin_site)
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
                 name='streamingcontent_download_csv'),
            path('analytics/',
                 self.admin_site.admin_view(self.analytics_view),
                 name='streamingcontent_analytics'),
        ]
        return custom_urls + urls

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

@admin.register(StreamingSubscription, site=admin_site)
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

@admin.register(StreamViewLog, site=admin_site)
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

@admin.register(StreamingRating, site=admin_site)
class StreamingRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'rating')
    list_filter = ('rating',)
    search_fields = ('userusername', 'contenttitle')

@admin.register(StreamingAnalyticsProxy, site=admin_site)
class StreamingAnalyticsProxyAdmin(admin.ModelAdmin):
    change_list_template = "admin/streaming/analytics_chart.html"
    list_display = ()

    def changelist_view(self, request, extra_context=None):
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

        total_views = sum(views)
        avg_completion_rate = round(sum(completion_rates) / len(completion_rates), 2) if completion_rates else 0
        total_unique_users = sum(unique_users)
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0

        category_qs = StreamingContent.objects.values("category").annotate(count=Count("id"))
        categories = [c["category"] for c in category_qs]
        category_counts = [c["count"] for c in category_qs]

        genre_qs = StreamingContent.objects.values("genre").annotate(count=Count("id"))
        genres = [g["genre"] for g in genre_qs]
        genre_counts = [g["count"] for g in genre_qs]

        lang_qs = StreamingContent.objects.values("language").annotate(count=Count("id"))
        languages = [l["language"] for l in lang_qs]
        language_counts = [l["count"] for l in lang_qs]

        country_qs = StreamViewLog.objects.values("country").annotate(total=Sum("views"))
        countries = [c["country"] or "Unknown" for c in country_qs]
        country_views = [c["total"] for c in country_qs]

        extra_context = extra_context or {}
        extra_context.update({
            "labels": labels,
            "views": views,
            "unique_users": unique_users,
            "completion_rates": completion_rates,
            "ratings": ratings,
            "total_views": total_views,
            "avg_completion_rate": avg_completion_rate,
            "total_unique_users": total_unique_users,
            "avg_rating": avg_rating,
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


class CustomAdminSite(AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        context['media'] += forms.Media(css={
            'all': ('css/admin_custom.css',)
        })
        return context
