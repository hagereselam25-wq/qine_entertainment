import uuid
from django.core.files.base import ContentFile
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, FileResponse, JsonResponse, HttpResponseBadRequest
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from io import BytesIO
from datetime import timedelta
import time
import hmac
import hashlib
import os
import qrcode
import json

import uuid
import json
import os
import time
import hmac
import hashlib
from io import BytesIO
from datetime import timedelta

import requests
import qrcode

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, FileResponse, JsonResponse, HttpResponseBadRequest
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import F, Sum, Count

from .models import (
    StreamingSubscription, StreamingContent,
    Transaction, StreamViewLog, UserProfile
)
from .forms import StreamingSubscriptionForm, CustomUserSignupForm, ProfileUpdateForm
from .utils import generate_signed_url


from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from django.db.models import F, Sum, Count

from .models import (
    StreamingSubscription, StreamingContent,
    Transaction, StreamViewLog, UserProfile
)
from .forms import StreamingSubscriptionForm, CustomUserSignupForm, ProfileUpdateForm
from .utils import generate_signed_url

CHAPA_BASE_URL = "https://api.chapa.co/v1"
CHAPA_SECRET_KEY = "CHASECK_TEST-LVVM7kiTEAfpgTT9ULzRH4qm4dtac79i"

SUBSCRIPTION_PRICES = {
    'monthly': 500.00,
    'annual': 5000.00,
}

# ---------------------------
# Subscription and Payment Views
# ---------------------------
def create_subscription(request):
    if request.method == 'POST':
        form = StreamingSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.amount = SUBSCRIPTION_PRICES[subscription.subscription_type]
            tx_ref = str(uuid.uuid4())
            subscription.chapa_tx_ref = tx_ref
            subscription.save()

            payload = {
                "amount": subscription.amount,
                "currency": "ETB",
                "email": subscription.email,
                "first_name": subscription.full_name,
                "tx_ref": tx_ref,
                "callback_url": request.build_absolute_uri('/streaming/verify/'),
                "return_url": request.build_absolute_uri(f'/streaming/verify/?tx_ref={tx_ref}'),
                "customization[title]": _("Streaming")
            }

            headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
            response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", data=payload, headers=headers)

            if response.status_code == 200 and response.json().get("status") == "success":
                payment_url = response.json()['data']['checkout_url']
                return redirect(payment_url)
            else:
                return HttpResponse(_("Failed to initialize Chapa payment. Response: %(response)s") % {'response': response.text}, status=500)
    else:
        form = StreamingSubscriptionForm()

    return render(request, 'streaming/create_subscription.html', {'form': form})

def verify_subscription_payment(request):
    tx_ref = request.GET.get('tx_ref')
    if not tx_ref:
        return HttpResponse(_("No transaction reference provided."))

    subscription = get_object_or_404(StreamingSubscription, chapa_tx_ref=tx_ref)

    if subscription.is_paid:
        return redirect(f'/streaming/thankyou/?tx_ref={tx_ref}')

    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
    response = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}", headers=headers)

    if response.status_code == 200 and response.json()['status'] == 'success':
        data = response.json()['data']
        if data['status'] == 'success':
            subscription.is_paid = True

            if subscription.subscription_type == 'monthly':
                subscription.access_expires_at = timezone.now() + timedelta(days=30)
            elif subscription.subscription_type == 'annual':
                subscription.access_expires_at = timezone.now() + timedelta(days=365)

            qr_data = _("CineHub Subscription\nName: %(name)s\nEmail: %(email)s\nType: %(type)s") % {
                'name': subscription.full_name,
                'email': subscription.email,
                'type': subscription.subscription_type
            }
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            file_name = f"{tx_ref}.png"
            subscription.qr_code.save(file_name, ContentFile(buffer.getvalue()))
            buffer.close()

            subscription.save()

            email = EmailMessage(
                subject=_("🎫 CineHub Subscription Confirmed"),
                body=_("Hi %(name)s,\n\nYour %(plan)s subscription is now active!\n\nThanks for choosing CineHub.") % {
                    'name': subscription.full_name,
                    'plan': subscription.subscription_type
                },
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[subscription.email],
            )
            if subscription.qr_code:
                email.attach_file(subscription.qr_code.path)
            email.send(fail_silently=True)

            return redirect(f'/streaming/thankyou/?tx_ref={tx_ref}')
        else:
            return HttpResponse(_("Payment not successful."))
    else:
        return HttpResponse(_("Payment verification failed."))

def subscription_thankyou(request):
    tx_ref = request.GET.get('tx_ref')
    subscription = StreamingSubscription.objects.filter(chapa_tx_ref=tx_ref).first()
    return render(request, 'streaming/thankyou.html', {'subscription': subscription})

# ---------------------------
# User Authentication Views
# ---------------------------
def user_signup(request):
    if request.method == 'POST':
        form = CustomUserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            login(request, user)

            plan = form.cleaned_data['plan']
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            amount = 500 if plan == 'monthly' else 5000
            tx_ref = f"sub-{uuid.uuid4()}"

            StreamingSubscription.objects.create(
                user=user,
                full_name=username,
                email=email,
                subscription_type=plan,
                chapa_tx_ref=tx_ref,
                amount=amount,
                is_paid=False
            )
            Transaction.objects.create(
                user=user,
                tx_ref=tx_ref,
                amount=amount,
                email=email,
                first_name=username,
                last_name='',
                status='initiated'
            )

            callback_url = request.build_absolute_uri(reverse('streaming:verify_subscription_payment'))
            chapa_payload = {
                "amount": str(amount),
                "currency": "ETB",
                "email": email,
                "first_name": username,
                "last_name": "",
                "tx_ref": tx_ref,
                "callback_url": callback_url,
                "return_url": f"{callback_url}?tx_ref={tx_ref}",
                "customization[title]": str(_("Streaming Subscription")),
                "customization[description]": str(_("%(plan)s subscription for streaming access") % {'plan': plan.capitalize()}),
            }

            headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
            response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", json=chapa_payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get('status') == 'success':
                return redirect(response_data['data']['checkout_url'])
            else:
                messages.error(request, _("Failed to initialize payment: %(response)s") % {'response': response_data})
                return redirect('streaming:signup')
    else:
        form = CustomUserSignupForm()

    return render(request, 'streaming/user_signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, _('Invalid credentials.'))
    return render(request, 'streaming/user_login.html')

def user_logout(request):
    logout(request)
    return redirect('home')

@login_required
def profile(request):
    subscription = StreamingSubscription.objects.filter(user=request.user, is_paid=True).first()
    return render(request, 'streaming/profile.html', {'subscription': subscription})

# ---------------------------
# Streaming Views with Metrics
# ---------------------------from django.db.models import Q
from collections import defaultdict

@login_required
def streaming_home(request):
    contents = StreamingContent.objects.all().order_by('-release_date')

    # Generate signed URLs
    for content in contents:
        if content.video_url and content.video_url.endswith('.m3u8'):
            base_url = request.build_absolute_uri(content.video_url)
            content.signed_url = generate_signed_url(video_id=str(content.pk), base_url=base_url)
        else:
            content.signed_url = content.video_file.url if content.video_file else ""

    # Get distinct values for filters
    categories = StreamingContent.objects.values_list("category", flat=True).distinct()
    genres = StreamingContent.objects.values_list("genre", flat=True).distinct()
    languages = StreamingContent.objects.values_list("language", flat=True).distinct()

    # Group by category for section display
    categorized_contents = defaultdict(list)
    for content in contents:
        categorized_contents[content.get_category_display()].append(content)

    context = {
        "contents": contents,
        "categories": categories,
        "genres": genres,
        "languages": languages,
        "categorized_contents": dict(categorized_contents),
    }

    return render(request, "streaming/streaming_home.html", context)
# ------------------- Watch Video -------------------
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import F, Avg
import os

from .models import StreamingContent, StreamingSubscription, StreamViewLog, StreamingRating
from .utils import generate_signed_url
from .forms import RatingForm  # We'll use a simple form for rating submission

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Avg
import os
from .models import StreamingContent, StreamingSubscription, StreamViewLog, StreamingRating
from .forms import RatingForm
from .utils import generate_signed_url
from django.conf import settings


# ------------------- Watch Video -------------------
@login_required
def watch_video(request, content_id):
    content = get_object_or_404(StreamingContent, id=content_id)
    subscription = StreamingSubscription.objects.filter(
        user=request.user,
        is_paid=True,
        access_expires_at__gt=timezone.now()
    ).first()
    if not subscription:
        return redirect('streaming:create_subscription')

    # HLS / video URL handling
    hls_dir = os.path.join(settings.MEDIA_ROOT, 'hls', str(content.id))
    master_m3u8 = os.path.join(hls_dir, 'master.m3u8')
    is_hls = os.path.exists(master_m3u8)
    video_file_url = content.video_file.url if not is_hls else ''
    base_url = request.build_absolute_uri(f"/media/hls/{content.id}/master.m3u8")
    signed_url = generate_signed_url(video_id=str(content.id), base_url=base_url) if is_hls else video_file_url

    # Log streaming (do not increment plays here anymore)
    log, created = StreamViewLog.objects.get_or_create(user=request.user, content=content)
    if created:
        content.unique_viewers += 1
        content.save(update_fields=['unique_viewers'])

    # Handle rating submission
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating_value = form.cleaned_data['rating']
            rating_obj, _ = StreamingRating.objects.update_or_create(
                user=request.user,
                content=content,
                defaults={'rating': rating_value}
            )
            # Recalculate average rating
            avg_rating = StreamingRating.objects.filter(content=content).aggregate(avg=Avg('rating'))['avg'] or 0
            content.average_rating = round(avg_rating, 2)
            content.save(update_fields=['average_rating'])
            return redirect('streaming:watch_video', content_id=content.id)
    else:
        try:
            existing_rating = StreamingRating.objects.get(user=request.user, content=content)
            form = RatingForm(initial={'rating': existing_rating.rating})
        except StreamingRating.DoesNotExist:
            form = RatingForm()

    context = {
        'content': content,
        'video_url': signed_url,
        'is_hls': is_hls,
        'log': log,
        'rating_form': form,
        'average_rating': content.average_rating or 0,
    }
    return render(request, 'streaming/watch_video.html', context)


# ------------------- Report Watch Time -------------------
@csrf_exempt
@require_POST
@login_required
def report_watch_time(request, content_id):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponseBadRequest(_("Invalid JSON"))

    event = payload.get('event')
    delta = payload.get('watched_seconds_delta')
    absolute = payload.get('watched_seconds')

    content = get_object_or_404(StreamingContent, id=content_id)
    log, created = StreamViewLog.objects.get_or_create(
        user=request.user,
        content=content,
        defaults={'views': 0, 'watch_time_seconds': 0}
    )

    if created:
        StreamingContent.objects.filter(pk=content.pk).update(unique_viewers=F('unique_viewers') + 1)

    if event == 'start':
        # Increment only when video actually starts
        StreamViewLog.objects.filter(pk=log.pk).update(views=F('views') + 1)
        StreamingContent.objects.filter(pk=content.pk).update(total_plays=F('total_plays') + 1)

    seconds_to_add = 0
    if isinstance(delta, (int, float)) and delta >= 0:
        seconds_to_add = int(delta)
    elif isinstance(absolute, (int, float)) and absolute >= 0:
        key = f'wt_{content_id}'
        last = request.session.get(key, 0)
        current = int(absolute)
        seconds_to_add = max(0, current - last)
        request.session[key] = current

    if seconds_to_add > 0:
        StreamViewLog.objects.filter(pk=log.pk).update(
            watch_time_seconds=F('watch_time_seconds') + seconds_to_add
        )
        StreamingContent.objects.filter(pk=content.pk).update(
            total_watch_time_seconds=F('total_watch_time_seconds') + seconds_to_add
        )

    total_seconds = StreamViewLog.objects.filter(content=content).aggregate(
        total=Sum('watch_time_seconds')
    )['total'] or 0
    denom_seconds = max(1, content.duration_minutes * 60 * max(1, content.total_plays))
    content.completion_rate = min(100.0, round(total_seconds / denom_seconds * 100, 2))
    content.save(update_fields=['completion_rate', 'total_watch_time_seconds'])

    return JsonResponse({
        'ok': True,
        'event': event,
        'added_seconds': seconds_to_add,
        'total_watch_time_minutes': total_seconds // 60,
        'completion_rate': float(content.completion_rate),
    })

# ------------------- User Profile -------------------
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, StreamViewLog
from .forms import ProfileUpdateForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, StreamViewLog
from .forms import ProfileUpdateForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile, WatchHistory  # make sure WatchHistory imported
from .forms import ProfileUpdateForm
from django.utils import timezone

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from .models import UserProfile, StreamViewLog
from .forms import ProfileUpdateForm

@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Get watch logs after last cleared time
    logs = StreamViewLog.objects.filter(user=request.user)
    if profile.history_cleared_at:
        logs = logs.filter(last_viewed__gt=profile.history_cleared_at)
    logs = logs.select_related('content').order_by('-last_viewed')

    watch_history = []
    total_watch_time = 0

    for log in logs:
        minutes = log.watch_time_seconds // 60
        total_watch_time += minutes
        watch_history.append({
            'video_title': log.content.title,
            'watch_date': log.last_viewed,
            'duration_watched': minutes,
        })

    total_videos = len(watch_history)

    # Profile picture update
    if request.method == "POST" and 'profile_picture' in request.FILES:
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('streaming:user_profile')
    else:
        form = ProfileUpdateForm(instance=profile)

    context = {
        'profile': profile,
        'form': form,
        'watch_history': watch_history,
        'total_videos': total_videos,
        'total_watch_time': total_watch_time,
    }

    return render(request, 'streaming/profile.html', context)

@login_required
def clear_watch_history(request):
    if request.method == "POST":
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.history_cleared_at = timezone.now()
        profile.save(update_fields=['history_cleared_at'])

        # Return JSON response with updated stats
        return JsonResponse({
            'success': True,
            'total_videos': 0,
            'total_watch_time': 0
        })

    return JsonResponse({'success': False}, status=400)

# ------------------- Admin Analytics -------------------
@staff_member_required
def streaming_analytics(request):
    content_stats = (
        StreamViewLog.objects
        .select_related('content', 'user', 'country')
        .values('content__title')
        .annotate(
            total_views=Sum('views'),
            unique_viewers=Count('user', distinct=True),
            total_watch_time=Sum('watch_time_seconds'),
            completion_rate=F('content__completion_rate')
        )
        .order_by('-total_views')
    )

    total_views = StreamViewLog.objects.aggregate(total=Sum('views'))['total'] or 0
    total_unique_viewers = StreamViewLog.objects.values('user').distinct().count()
    total_watch_time_seconds = StreamViewLog.objects.aggregate(total=Sum('watch_time_seconds'))['total'] or 0

    country_stats = (
        StreamViewLog.objects
        .values('country__name')
        .annotate(
            total_views=Sum('views'),
            unique_viewers=Count('user', distinct=True),
        )
        .order_by('-total_views')
    )

    context = {
        'content_stats': content_stats,
        'total_views': total_views,
        'total_unique_viewers': total_unique_viewers,
        'total_watch_time_minutes': total_watch_time_seconds // 60,
        'country_stats': country_stats
    }

    return render(request, "streaming/analytics.html", context)


@staff_member_required
def export_analytics_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="streaming_analytics.csv"'

    import csv
    writer = csv.writer(response)
    writer.writerow([
        _('Content'), _('Total Views'), _('Unique Viewers'),
        _('Total Watch Time (mins)'), _('Completion Rate (%)')
    ])

    content_stats = (
        StreamViewLog.objects
        .select_related('content', 'user')
        .values('content__title', 'content__completion_rate')
        .annotate(
            total_views=Sum('views'),
            unique_viewers=Count('user', distinct=True),
            total_watch_time=Sum('watch_time_seconds')
        )
        .order_by('-total_views')
    )

    for stat in content_stats:
        writer.writerow([
            stat['content__title'],
            stat['total_views'] or 0,
            stat['unique_viewers'] or 0,
            (stat['total_watch_time'] or 0) // 60,
            stat['content__completion_rate'] or 0
        ])

    return response


from django.db.models import Avg, Count

@login_required
@require_POST
def rate_video(request, content_id):
    content = get_object_or_404(StreamingContent, id=content_id)
    form = RatingForm(request.POST)

    if form.is_valid():
        rating_value = form.cleaned_data['rating']

        # Save or update the rating
        rating_obj, created = StreamingRating.objects.update_or_create(
            user=request.user,
            content=content,
            defaults={'rating': rating_value}
        )

        # Force refresh from DB
        agg = StreamingRating.objects.filter(content=content).aggregate(
            avg=Avg('rating'),
            total=Count('id')
        )
        print("DEBUG:", agg)  # 👈 Check console

        # Save into StreamingContent
        content.average_rating = agg['avg'] or 0
        content.total_ratings = agg['total'] or 0
        content.save(update_fields=['average_rating', 'total_ratings'])

        return JsonResponse({
            'ok': True,
            'average_rating': round(content.average_rating, 2),
            'total_ratings': content.total_ratings
        })

    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)