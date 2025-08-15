import uuid
from django.core.files.base import ContentFile
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from io import BytesIO
from datetime import timedelta
import time
import hmac
import hashlib
import os
import qrcode

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User

from .models import (
    StreamingSubscription, StreamingContent,
    Transaction, StreamViewLog
)
from .forms import StreamingSubscriptionForm, CustomUserSignupForm
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
                "customization[title]": "Streaming"
            }

            headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
            response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", data=payload, headers=headers)

            if response.status_code == 200 and response.json().get("status") == "success":
                payment_url = response.json()['data']['checkout_url']
                return redirect(payment_url)
            else:
                return HttpResponse(f"Failed to initialize Chapa payment. Response: {response.text}", status=500)
    else:
        form = StreamingSubscriptionForm()

    return render(request, 'streaming/create_subscription.html', {'form': form})

def verify_subscription_payment(request):
    tx_ref = request.GET.get('tx_ref')
    if not tx_ref:
        return HttpResponse("No transaction reference provided.")

    subscription = get_object_or_404(StreamingSubscription, chapa_tx_ref=tx_ref)

    if subscription.is_paid:
        return redirect(f'/streaming/thankyou/?tx_ref={tx_ref}')

    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}"}
    response = requests.get(f"{CHAPA_BASE_URL}/transaction/verify/{tx_ref}", headers=headers)

    if response.status_code == 200 and response.json()['status'] == 'success':
        data = response.json()['data']
        if data['status'] == 'success':
            subscription.is_paid = True

            # Set expiration
            if subscription.subscription_type == 'monthly':
                subscription.access_expires_at = timezone.now() + timedelta(days=30)
            elif subscription.subscription_type == 'annual':
                subscription.access_expires_at = timezone.now() + timedelta(days=365)

            # Generate QR
            qr_data = f"CineHub Subscription\nName: {subscription.full_name}\nEmail: {subscription.email}\nType: {subscription.subscription_type}"
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            file_name = f"{tx_ref}.png"
            subscription.qr_code.save(file_name, ContentFile(buffer.getvalue()))
            buffer.close()

            subscription.save()

            # Send confirmation email with QR attachment
            email = EmailMessage(
                subject="🎫 CineHub Subscription Confirmed",
                body=f"Hi {subscription.full_name},\n\nYour {subscription.subscription_type} subscription is now active!\n\nThanks for choosing CineHub.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[subscription.email],
            )
            if subscription.qr_code:
                email.attach_file(subscription.qr_code.path)
            email.send(fail_silently=True)

            return redirect(f'/streaming/thankyou/?tx_ref={tx_ref}')
        else:
            return HttpResponse("Payment not successful.")
    else:
        return HttpResponse("Payment verification failed.")

def subscription_thankyou(request):
    tx_ref = request.GET.get('tx_ref')
    subscription = StreamingSubscription.objects.filter(chapa_tx_ref=tx_ref).first()
    return render(request, 'streaming/thankyou.html', {'subscription': subscription})

# ---------------------------
# User Authentication Views
# ---------------------------
class CustomUserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    plan = forms.ChoiceField(choices=[('monthly', 'Monthly'), ('annual', 'Annual')])
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "plan")

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

            # Create subscription & transaction
            StreamingSubscription.objects.create(
                user=user, full_name=username, email=email,
                subscription_type=plan, chapa_tx_ref=tx_ref,
                amount=amount, is_paid=False
            )
            Transaction.objects.create(
                user=user, tx_ref=tx_ref, amount=amount,
                email=email, first_name=username, last_name='', status='initiated'
            )

            # Initialize Chapa payment
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
                "customization[title]": "Streaming Subscription",
                "customization[description]": f"{plan.capitalize()} subscription for streaming access",
            }
            headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
            response = requests.post(f"{CHAPA_BASE_URL}/transaction/initialize", json=chapa_payload, headers=headers)
            response_data = response.json()
            if response.status_code == 200 and response_data.get('status') == 'success':
                return redirect(response_data['data']['checkout_url'])
            else:
                messages.error(request, f"Failed to initialize payment: {response_data}")
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
            messages.error(request, 'Invalid credentials.')
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
# ---------------------------
def streaming_home(request):
    contents = StreamingContent.objects.all().order_by('-release_date')
    for content in contents:
        base_url = request.build_absolute_uri(f"/media/hls/{content.pk}/master.m3u8")
        content.signed_url = generate_signed_url(video_id=str(content.pk), base_url=base_url)
    return render(request, 'streaming/streaming_home.html', {'contents': contents})

@login_required
def watch_video(request, content_id):
    content = get_object_or_404(StreamingContent, id=content_id)

    # --- Subscription check ---
    subscription = StreamingSubscription.objects.filter(
        user=request.user,
        is_paid=True,
        access_expires_at__gt=timezone.now()
    ).first()

    if not subscription:
        return redirect('streaming:create_subscription')

    # --- Determine video type ---
    video_file_url = content.video_file.url  # Your uploaded video field
    is_hls = video_file_url.lower().endswith('.m3u8')

    # --- Signed URL for HLS (if needed) ---
    signed_url = video_file_url
    if is_hls:
        base_url = request.build_absolute_uri(f"/media/hls/{content.pk}/master.m3u8")
        signed_url = generate_signed_url(video_id=str(content.pk), base_url=base_url)

    # --- Log views ---
    log, created = StreamViewLog.objects.get_or_create(user=request.user, content=content)
    if created:
        content.unique_viewers += 1
    content.total_plays += 1
    content.save()

    context = {
        'content': content,
        'video_url': signed_url,
        'is_hls': is_hls,
        'log': log
    }

    return render(request, 'streaming/watch_video.html', context)

@login_required
def stream_video(request):
    video_id = request.GET.get('video_id')
    expires = request.GET.get('expires')
    signature = request.GET.get('signature')
    if not video_id or not expires or not signature:
        raise Http404("Missing parameters")

    try:
        expires = int(expires)
    except ValueError:
        raise Http404("Invalid expiration timestamp")

    if time.time() > expires:
        return HttpResponse("URL expired", status=403)

    # Validate signature
    data = f"{video_id}:{expires}"
    expected_signature = hmac.new(settings.STREAM_SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        return HttpResponse("Invalid signature", status=403)

    # Subscription check
    if not request.user.is_authenticated:
        return HttpResponse("You must be logged in to stream this video", status=401)
    subscription = StreamingSubscription.objects.filter(user=request.user, access_expires_at__gt=timezone.now()).first()
    if not subscription:
        return HttpResponse("You do not have an active subscription", status=403)

    video = get_object_or_404(StreamingContent, id=video_id)
    video_path = os.path.join(settings.MEDIA_ROOT, 'secure_videos', f"{video_id}.mp4")
    if not os.path.exists(video_path):
        raise Http404("Video not found")
    return FileResponse(open(video_path, 'rb'), content_type='video/mp4')

# ---------------------------
# API endpoint to report watch time
# ---------------------------
from django.contrib.gis.geoip2 import GeoIP2
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib.gis.geoip2 import GeoIP2  # requires GeoIP2 library
from django.utils.timezone import now
from django.contrib.gis.geoip2 import GeoIP2

@login_required
def report_watch_time(request):
    """
    Called via JS from watch_video.html periodically.
    POST data: content_id, watch_time_minutes
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    try:
        content_id = int(request.POST.get('content_id'))
        watch_time = int(request.POST.get('watch_time', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    content = get_object_or_404(StreamingContent, id=content_id)

    # Get country from IP
    try:
        ip = get_client_ip(request)
        g = GeoIP2()
        country = g.country(ip)['country_name']
    except Exception:
        country = "Unknown"

    # Update or create the stream log
    log, created = StreamViewLog.objects.get_or_create(
        user=request.user,
        content=content,
        defaults={'country': country, 'watch_time_minutes': 0}
    )
    log.watch_time_minutes += watch_time
    log.last_viewed = timezone.now()
    log.country = country
    log.save()

    # Update aggregate metrics
    content.total_watch_time_minutes = (
        StreamViewLog.objects.filter(content=content)
        .aggregate(total=models.Sum('watch_time_minutes'))['total'] or 0
    )
    total_views = content.total_plays if content.total_plays > 0 else 1
    content.completion_rate = (
        (content.total_watch_time_minutes / (total_views * content.duration_minutes)) * 100
        if content.duration_minutes else 0
    )
    content.save()

    return JsonResponse({
        'status': 'ok',
        'total_watch_time': content.total_watch_time_minutes,
        'country': country
    })


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import StreamViewLog, StreamingContent
from django.utils import timezone

# --- Reporting endpoint ---
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone

from .models import StreamingContent, StreamViewLog

@require_POST
@login_required
def report_watch_time(request, content_id):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    event = payload.get('event')
    delta = payload.get('watched_seconds_delta')
    absolute = payload.get('watched_seconds')  # fallback if you ever send absolute

    content = get_object_or_404(StreamingContent, id=content_id)
    log, created = StreamViewLog.objects.get_or_create(
        user=request.user,
        content=content,
        defaults={'views': 0, 'watch_time_minutes': 0}
    )

    # --- On first log creation, count unique viewer ---
    if created:
        StreamingContent.objects.filter(pk=content.pk).update(unique_viewers=F('unique_viewers') + 1)

    # --- Handle "start" (count a play) ---
    if event == 'start':
        # Count a "view" per session start
        StreamViewLog.objects.filter(pk=log.pk).update(views=F('views') + 1)
        StreamingContent.objects.filter(pk=content.pk).update(total_plays=F('total_plays') + 1)

    # --- Handle progress (time) ---
    # Prefer delta (seconds actually watched). If not provided, compute from absolute with session storage.
    seconds_to_add = 0
    if isinstance(delta, (int, float)) and delta >= 0:
        seconds_to_add = int(delta)
    elif isinstance(absolute, (int, float)) and absolute >= 0:
        key = f'wt_{content_id}'
        last = request.session.get(key, 0)
        current = int(absolute)
        diff = max(0, current - last)
        request.session[key] = current
        seconds_to_add = diff

    if seconds_to_add > 0:
        minutes_to_add = seconds_to_add // 60  # store in minutes
        if minutes_to_add > 0:
            StreamViewLog.objects.filter(pk=log.pk).update(
                watch_time_minutes=F('watch_time_minutes') + minutes_to_add
            )
            StreamingContent.objects.filter(pk=content.pk).update(
                total_watch_time_minutes=F('total_watch_time_minutes') + minutes_to_add
            )

    # --- Recompute completion rate (best-effort) ---
    content.refresh_from_db(fields=['total_watch_time_minutes', 'duration_minutes', 'total_plays'])
    denom = max(1, content.duration_minutes * max(1, content.total_plays))
    completion = min(100.0, round((content.total_watch_time_minutes / denom) * 100.0, 2))
    if completion != content.completion_rate:
        content.completion_rate = completion
        content.save(update_fields=['completion_rate'])

    return JsonResponse({
        'ok': True,
        'event': event,
        'added_seconds': seconds_to_add,
        'total_watch_time_minutes': content.total_watch_time_minutes,
        'completion_rate': float(content.completion_rate),
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile, WatchHistory
from .forms import ProfileUpdateForm

@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    watch_history = WatchHistory.objects.filter(user=request.user).order_by('-watch_date')

    total_videos = watch_history.count()
    total_watch_time = sum([w.duration_watched for w in watch_history])

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('user_profile')
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
