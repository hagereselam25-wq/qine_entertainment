import uuid
from django.core.files.base import ContentFile
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from io import BytesIO
from .forms import StreamingSubscriptionForm
from .models import StreamingSubscription
import qrcode
from datetime import timedelta
from .forms import CustomUserSignupForm

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
import requests
import uuid

from django.contrib.auth.models import User
from .models import StreamingSubscription, Transaction


CHAPA_BASE_URL = "https://api.chapa.co/v1"
CHAPA_SECRET_KEY = "CHASECK_TEST-LVVM7kiTEAfpgTT9ULzRH4qm4dtac79i"

SUBSCRIPTION_PRICES = {
    'monthly': 500.00,
    'annual': 5000.00,
}

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

            headers = {
                "Authorization": f"Bearer {CHAPA_SECRET_KEY}"
            }

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

    return render(request, 'streaming/thankyou.html', {
        'subscription': subscription
    })





# User signup view
import uuid
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
import requests
from django.utils import timezone
import uuid
import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.models import User

from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth.models import User
import uuid
import requests
from django.conf import settings


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
import requests
import uuid

from django.contrib.auth.models import User
from .models import StreamingSubscription, Transaction  # Adjust import paths if needed


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')  # or change to your desired landing page
        else:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'streaming/user_login.html')

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
import uuid
import requests
from .models import StreamingSubscription, Transaction
from django.conf import settings


from django.contrib.auth.forms import UserCreationForm
from django import forms

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

            # Create unpaid subscription record
            StreamingSubscription.objects.create(
                user=user,
                full_name=username,
                email=email,
                chapa_tx_ref=tx_ref,
                subscription_type=plan,
                amount=amount,
                is_paid=False,
            )

            # Create transaction record
            Transaction.objects.create(
                user=user,
                tx_ref=tx_ref,
                amount=amount,
                email=email,
                first_name=username,
                last_name='',
                status='initiated',
            )

            # Prepare Chapa payment
            callback_url = request.build_absolute_uri(reverse('streaming:verify_subscription_payment'))

            chapa_payload = {
                "amount": str(amount),
                "currency": "ETB",
                "email": email,
                "first_name": username,
                "last_name": "",
                "tx_ref": tx_ref,
                "callback_url": callback_url,
                "return_url": f"{callback_url}?tx_ref={tx_ref}",  # Important: append tx_ref here
                "customization[title]": "Streaming Subscription",
                "customization[description]": f"{plan.capitalize()} subscription for streaming access",
            }

            headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
            chapa_url = "https://api.chapa.co/v1/transaction/initialize"
            response = requests.post(chapa_url, json=chapa_payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get('status') == 'success':
                return redirect(response_data['data']['checkout_url'])
            else:
                messages.error(request, f"Failed to initialize payment: {response_data}")
                return redirect('streaming:signup')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CustomUserSignupForm()

    return render(request, 'streaming/user_signup.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('home')  # or your preferred landing page


from django.contrib.auth.decorators import login_required
from django.shortcuts import render


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import StreamingSubscription

@login_required
def profile(request):
    # Get the active paid subscription for this user, if any
    subscription = StreamingSubscription.objects.filter(user=request.user, is_paid=True).first()
    
    return render(request, 'streaming/profile.html', {
        'subscription': subscription
    })
