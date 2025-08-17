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
@login_required
def streaming_home(request):
    contents = StreamingContent.objects.all().order_by('-release_date')
    for content in contents:
        if content.video_url and content.video_url.endswith('.m3u8'):
            base_url = request.build_absolute_uri(content.video_url)
            content.signed_url = generate_signed_url(video_id=str(content.pk), base_url=base_url)
        else:
            content.signed_url = content.video_file.url if content.video_file else ""
    return render(request, 'streaming/streaming_home.html', {'contents': contents})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import StreamingContent, StreamingSubscription, StreamViewLog

import os
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.db.models import F, Sum
from django.conf import settings

from .models import StreamingContent, StreamViewLog, StreamingSubscription, UserProfile
from .forms import ProfileUpdateForm
from .utils import generate_signed_url

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

    # Check if HLS exists
    hls_dir = os.path.join(settings.MEDIA_ROOT, 'hls', str(content.id))
    master_m3u8 = os.path.join(hls_dir, 'master.m3u8')
    is_hls = os.path.exists(master_m3u8)
    video_file_url = content.video_file.url if not is_hls else ''

    base_url = request.build_absolute_uri(f"/media/hls/{content.id}/master.m3u8")
    signed_url = generate_signed_url(video_id=str(content.id), base_url=base_url) if is_hls else video_file_url

    log, created = StreamViewLog.objects.get_or_create(user=request.user, content=content)
    if created:
        content.unique_viewers += 1
    content.total_plays += 1
    content.save(update_fields=['unique_viewers', 'total_plays'])

    context = {
        'content': content,
        'video_url': signed_url,
        'is_hls': is_hls,
        'log': log
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
        return HttpResponseBadRequest("Invalid JSON")

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
@login_required
def user_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    logs = StreamViewLog.objects.filter(user=request.user).select_related('content').order_by('-last_viewed')

    watch_history = []
    total_watch_time = 0
    for log in logs:
        minutes = log.watch_time_seconds // 60
        total_watch_time += minutes
        watch_history.append({
            'video_title': log.content.title,
            'watch_date': log.last_viewed,
            'duration_watched': minutes,
            'completion_rate': log.content.completion_rate,
            'country': log.country.name if log.country else 'Unknown'
        })

    total_videos = len(watch_history)

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