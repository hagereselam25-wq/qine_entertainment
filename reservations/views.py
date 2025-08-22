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
from django.utils.translation import gettext_lazy as _
from django.core.files.storage import default_storage


# Home page: shows all available movies (with search)
@login_required
def video_detail(request, pk):
    """Secure access to a single video."""
    video = get_object_or_404(Video, pk=pk)

    # Access control logic
    if not video.is_public and video.uploaded_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_("You don't have permission to view this video."))

    return render(request, 'videos/video_detail.html', {'video': video})


from django.shortcuts import render
from .models import Movie, Rating
from streaming.models import StreamingContent

def home(request):
    query = request.GET.get('q')

    # Cinema movies
    if query:
        movies = Movie.objects.filter(title__icontains=query)
    else:
        movies = Movie.objects.all()

    # Calculate average rating for cinema movies
    for movie in movies:
        ratings = Rating.objects.filter(movie=movie)
        movie.average_rating = sum(r.rating for r in ratings)/len(ratings) if ratings.exists() else 0

    # Featured streaming content
    featured_streaming = StreamingContent.objects.order_by('-release_date')[:6]  # latest 10

    return render(request, 'reservations/home.html', {
        'movies': movies,
        'query': query,
        'featured_movies': movies[:6],  # featured cinema movies
        'featured_streaming': featured_streaming,  # featured streaming content
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
                raise ValueError(_("Invalid amount"))
        except:
            return render(request, 'reservations/seat_selection.html', {
                'movie': movie,
                'seats': seats,
                'error': _('Please enter a valid payment amount.')
            })

        try:
            seat = Seat.objects.select_for_update().get(id=seat_id, movie=movie)

            if seat.is_booked:
                return render(request, 'reservations/seat_selection.html', {
                    'movie': movie,
                    'seats': seats,
                    'error': _('Seat already booked.')
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
                "customization[title]": _(f"Ticket for {movie.title}"),
                "customization[description]": _("Cinema seat booking")
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
                    'error': _('Payment initialization failed. Try again.')
                })

        except Seat.DoesNotExist:
            return render(request, 'reservations/seat_selection.html', {
                'movie': movie,
                'seats': seats,
                'error': _('Invalid seat.')
            })

    return render(request, 'reservations/seat_selection.html', {
        'movie': movie,
        'seats': seats
    })


def payment_success(request):
    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return render(request, "reservations/payment_failed.html", {"error": _("Transaction reference missing.")})

    url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
    response = requests.get(url, headers=headers)
    chapa_data = response.json()

    if chapa_data.get("status") != "success":
        return render(request, "reservations/payment_failed.html", {"error": _("Payment verification failed.")})

    try:
        transaction = Transaction.objects.get(transaction_id=tx_ref)
        reservation = transaction.reservation
    except Transaction.DoesNotExist:
        return render(request, "reservations/payment_failed.html", {"error": _("Transaction not found.")})

    if not reservation.is_paid:
        reservation.is_paid = True
        reservation.save()

        transaction.status = "success"
        transaction.save()

        qr = qrcode.make(_(f"Reservation ID: {reservation.id} - Seat: {reservation.seat.seat_number}"))
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        reservation.qr_code.save(f"qr_{reservation.id}.png", ContentFile(buffer.getvalue()))
        buffer.close()

    # Send email only if not sent yet
    if not reservation.email_sent:
        subject = _("🎟 Your Cinema Ticket Confirmation")
        message = _(f"Dear {reservation.user},\n\nYour ticket has been confirmed. Seat: {reservation.seat.seat_number}")

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
        return HttpResponse(_("Ticket is not paid yet. Please complete payment to access."))
    return render(request, 'reservations/ticket_confirmation.html', {
        'reservation': reservation
    })

import base64
from io import BytesIO
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _
import qrcode
import requests
from .models import Reservation, Transaction, Movie, Seat
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile


def payment_verify(request):
    tx_ref = request.GET.get('tx_ref')
    if not tx_ref:
        return render(request, "reservations/payment_failed.html", {"error": _("Missing tx_ref.")})

    try:
        transaction = Transaction.objects.get(transaction_id=tx_ref)
        reservation = transaction.reservation
    except Transaction.DoesNotExist:
        return render(request, "reservations/payment_failed.html", {"error": _("Transaction not found.")})

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
        qr = qrcode.make(_(f"Reservation ID: {reservation.id}, Seat: {reservation.seat.seat_number}, Movie: {reservation.movie.title}"))
        buffer = BytesIO()
        qr.save(buffer)
        filename = f"ticket_qr_{reservation.id}.png"
        reservation.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        reservation.save()

        transaction.status = "success"
        transaction.save()

        # Send confirmation email with QR
        subject = _("🎟 Your Cinema Ticket Confirmation")
        message = _(f"""
Hello {reservation.user},

✅ Your payment for '{reservation.movie.title}' has been confirmed.

🎫 Seat: {reservation.seat.seat_number}
📍 Movie: {reservation.movie.title}

Please show the attached QR code at the entrance.

Enjoy your show!
""")
        email = EmailMessage(subject, message, to=[reservation.email])
        email.attach(filename, buffer.getvalue(), 'image/png')
        email.send()

        return redirect('ticket_confirmation', reservation_id=reservation.id)

    else:
        transaction.status = "failed"
        transaction.save()
        return render(request, "reservations/payment_failed.html", {"error": _("Payment verification failed.")})


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
            messages.error(request, _('Invalid credentials or not authorized.'))

    return render(request, 'reservations/admin_login.html')


# Admin logout view
def admin_logout(request):
    logout(request)
    return redirect('home')

# Thank you page after successful payment
def thank_you(request):
    reservation = Reservation.objects.filter(is_paid=True).last()
    return render(request, "reservations/thank_you.html", {"reservation": reservation})



from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

def contact_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        feedback = request.POST.get("feedback")

        if name and email and feedback:
            # Send feedback email to host
            send_mail(
                subject=f"Feedback from {name}",
                message=f"Sender: {name}\nEmail: {email}\n\nFeedback:\n{feedback}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],  # your host email
                fail_silently=False,
            )
            # Pass a flag to trigger JS alert
            return render(request, 'reservations/contact.html', {'success': True})
        else:
            messages.error(request, "Please fill in all fields.")

    return render(request, 'reservations/contact.html')

from django.shortcuts import render

def about_view(request):
    return render(request, 'reservations/about.html')


from django.shortcuts import render
from .models import Movie

from django.shortcuts import render
from .models import Movie

def cinema(request):
    query = request.GET.get('q', '')  # get search query from GET
    if query:
        movies = Movie.objects.filter(title__icontains=query).order_by('show_time')
    else:
        movies = Movie.objects.all().order_by('show_time')  # show upcoming first

    return render(request, 'reservations/cinema.html', {
        'movies': movies,
        'query': query
    })