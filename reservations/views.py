import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMessage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Movie, Seat, Reservation, Rating, Transaction
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from django.core.files.storage import default_storage


# Home page: shows all available movies (with search)
@login_required
def video_detail(request, pk):
    """Secure access to a single video."""
    video = get_object_or_404(Video, pk=pk)

    # Access control logic
    if not video.is_public and video.uploaded_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("You don't have permission to view this video.")

    return render(request, 'videos/video_detail.html', {'video': video})


def home(request):
    query = request.GET.get('q')
    if query:
        movies = Movie.objects.filter(title__icontains=query)
    else:
        movies = Movie.objects.all()

    # For calculating average rating (if using the Rating model)
    for movie in movies:
        ratings = Rating.objects.filter(movie=movie)
        if ratings.exists():
            movie.average_rating = sum(r.rating for r in ratings) / len(ratings)
        else:
            movie.average_rating = 0  # No ratings yet
    
    return render(request, 'reservations/home.html', {
        'movies': movies,
        'query': query
    })


# Movie list page
def movie_list(request):
    movies = Movie.objects.all()
    return render(request, 'reservations/movie_list.html', {'movies': movies})


def seat_selection(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    seats = Seat.objects.filter(movie=movie).order_by('seat_number')

    if request.method == "POST":
        seat_id = request.POST.get('seat_id')
        name = request.POST.get('name')
        email = request.POST.get('email')
        amount = request.POST.get('amount')

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Invalid amount")
        except:
            return render(request, 'reservations/seat_selection.html', {
                'movie': movie,
                'seats': seats,
                'error': 'Please enter a valid payment amount.'
            })

        try:
            seat = Seat.objects.select_for_update().get(id=seat_id, movie=movie)

            if seat.is_booked:
                return render(request, 'reservations/seat_selection.html', {
                    'movie': movie,
                    'seats': seats,
                    'error': 'Seat already booked.'
                })

            seat.is_booked = True
            seat.save()

            reservation = Reservation.objects.create(
                movie=movie,
                seat=seat,
                user=name,
                email=email,
                is_paid=False
            )

            tx_ref = f"reservation_{reservation.id}"

            Transaction.objects.create(
                reservation=reservation,
                transaction_id=tx_ref,
                amount=amount,
                status='pending'
            )

            chapa_data = {
                "amount": str(amount),
                "currency": "ETB",
                "email": email,
                "first_name": name,
                "tx_ref": tx_ref,
                "callback_url": request.build_absolute_uri("/payment/verify/"),
                "return_url": request.build_absolute_uri(f"/payment/success/?tx_ref={tx_ref}"),
                "customization[title]": f"Ticket for {movie.title}",
                "customization[description]": "Cinema seat booking"
            }

            headers = {
                "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            chapa_response = requests.post(settings.CHAPA_BASE_URL, json=chapa_data, headers=headers)
            response_data = chapa_response.json()

            if chapa_response.status_code == 200 and response_data.get("status") == "success":
                return redirect(response_data["data"]["checkout_url"])
            else:
                seat.is_booked = False
                seat.save()
                reservation.delete()
                return render(request, 'reservations/seat_selection.html', {
                    'movie': movie,
                    'seats': seats,
                    'error': 'Payment initialization failed. Try again.'
                })

        except Seat.DoesNotExist:
            return render(request, 'reservations/seat_selection.html', {
                'movie': movie,
                'seats': seats,
                'error': 'Invalid seat.'
            })

    return render(request, 'reservations/seat_selection.html', {
        'movie': movie,
        'seats': seats
    })


import requests
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
from django.shortcuts import render, get_object_or_404
from .models import Reservation, Transaction
from django.conf import settings

from django.core.mail import EmailMessage

def payment_success(request):
    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return render(request, "reservations/payment_failed.html", {"error": "Transaction reference missing."})

    url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    chapa_data = response.json()

    if chapa_data.get("status") != "success":
        return render(request, "reservations/payment_failed.html", {"error": "Payment verification failed."})

    try:
        transaction = Transaction.objects.get(transaction_id=tx_ref)
        reservation = transaction.reservation
    except Transaction.DoesNotExist:
        return render(request, "reservations/payment_failed.html", {"error": "Transaction not found."})

    if not reservation.is_paid:
        reservation.is_paid = True
        reservation.save()

        transaction.status = "success"
        transaction.save()

        qr = qrcode.make(f"Reservation ID: {reservation.id} - Seat: {reservation.seat.seat_number}")
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        reservation.qr_code.save(f"qr_{reservation.id}.png", ContentFile(buffer.getvalue()))
        buffer.close()

    # Send email only if not sent yet
    if not reservation.email_sent:
        subject = "🎟 Your Cinema Ticket Confirmation"
        message = f"Dear {reservation.user},\n\nYour ticket has been confirmed. Seat: {reservation.seat.seat_number}"

        email_msg = EmailMessage(subject, message, to=[reservation.email])
        email_msg.attach(f"ticket_qr_{reservation.id}.png", reservation.qr_code.read(), "image/png")
        email_msg.send()

        reservation.email_sent = True
        reservation.save()

    return render(request, "reservations/payment_success.html", {
        "reservation": reservation,
        "qr_url": reservation.qr_code.url if reservation.qr_code else None,
    })



# Ticket confirmation page
def ticket_confirmation(request, ticket_id):
    reservation = get_object_or_404(Reservation, id=ticket_id)
    if not reservation.is_paid:
        return HttpResponse("Ticket is not paid yet. Please complete payment to access.")
    return render(request, 'reservations/ticket_confirmation.html', {
        'reservation': reservation
    })

from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Reservation, Transaction
import qrcode
from io import BytesIO
import base64

import base64
from io import BytesIO
from django.conf import settings
from django.shortcuts import render
from django.core.mail import EmailMessage
import qrcode
from .models import Reservation, Transaction


from django.core.mail import EmailMessage
from django.conf import settings
from django.shortcuts import render
from .models import Reservation, Transaction
import qrcode
import base64
from io import BytesIO

from django.shortcuts import render
from .models import Reservation, Transaction
import qrcode
import base64
from io import BytesIO
from django.core.mail import EmailMessage
from django.conf import settings

from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import EmailMessage
from .models import Reservation, Transaction
import requests
import qrcode
from io import BytesIO
import base64

import qrcode
import base64
import requests
from io import BytesIO
from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect
from .models import Reservation, Transaction

def payment_verify(request):
    tx_ref = request.GET.get('tx_ref')
    if not tx_ref:
        return render(request, "reservations/payment_failed.html", {"error": "Missing tx_ref."})

    try:
        transaction = Transaction.objects.get(transaction_id=tx_ref)
        reservation = transaction.reservation
    except Transaction.DoesNotExist:
        return render(request, "reservations/payment_failed.html", {"error": "Transaction not found."})

    # Check if already verified
    if reservation.is_paid:
        return redirect('ticket_confirmation', reservation_id=reservation.id)

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"
    }

    verify_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    response = requests.get(verify_url, headers=headers)
    result = response.json()

    if result.get("status") == "success" and result["data"]["status"] == "success":
        # ✅ Update reservation and transaction
        reservation.is_paid = True

        # Generate QR code
        qr = qrcode.make(f"Reservation ID: {reservation.id}, Seat: {reservation.seat.seat_number}, Movie: {reservation.movie.title}")
        buffer = BytesIO()
        qr.save(buffer)
        filename = f"ticket_qr_{reservation.id}.png"
        reservation.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        reservation.save()

        transaction.status = "success"
        transaction.save()

        # Send confirmation email with QR
        subject = "🎟️ Your Cinema Ticket Confirmation"
        message = f"""
Hello {reservation.user},

✅ Your payment for '{reservation.movie.title}' has been confirmed.

🎫 Seat: {reservation.seat.seat_number}
📍 Movie: {reservation.movie.title}

Please show the attached QR code at the entrance.

Enjoy your show!
"""
        email = EmailMessage(subject, message, to=[reservation.email])
        email.attach(filename, buffer.getvalue(), 'image/png')
        email.send()

        return redirect('ticket_confirmation', reservation_id=reservation.id)

    else:
        transaction.status = "failed"
        transaction.save()
        return render(request, "reservations/payment_failed.html", {"error": "Payment verification failed."})


def payment_cancel(request):
    return render(request, 'reservations/payment_cancel.html')



# Admin dashboard view
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    movies = Movie.objects.all()
    reservations = Reservation.objects.select_related('movie', 'seat').all().order_by('-id')
    seats = Seat.objects.select_related('movie').all().order_by('movie__title', 'seat_number')

    return render(request, 'reservations/admin_dashboard.html', {
        'movies': movies,
        'reservations': reservations,
        'seats': seats
    })


# Admin login view
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not authorized.')

    return render(request, 'reservations/admin_login.html')


# Admin logout view
def admin_logout(request):
    logout(request)
    return redirect('home')


# Payment verification view with QR code generation and transaction update

# Thank you page after successful payment
def thank_you(request):
    reservation = Reservation.objects.filter(is_paid=True).last()
    return render(request, "reservations/thank_you.html", {"reservation": reservation})
