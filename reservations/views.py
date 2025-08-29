import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMessage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Movie, Seat, Reservation, Transaction
import requests
from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from streaming.models import StreamingContent


def home(request):
    query = request.GET.get('q')

    # search query for cinema and events
    if query:
        movies = Movie.objects.filter(title__icontains=query)
    else:
        movies = Movie.objects.all()

    # featured streaming content fetches at least six streaming contents on the home
    featured_streaming = StreamingContent.objects.order_by('-release_date')[:6]  

    #renders the home.html template and passes context
    return render(request, 'reservations/home.html', {
        'movies': movies,
        'query': query,
        'featured_movies': movies[:6],  # featured cinema movies
        'featured_streaming': featured_streaming,  # featured streaming content
    })




from django.shortcuts import render, get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from reservations.models import Movie, Seat, Reservation, Transaction
import requests



import uuid  

def seat_selection(request, movie_id):
    # fetches the movie by movie_id, returns 404 if it doesn’t exist, fetches all seats for that movie and orders them by seat number for display
    movie = get_object_or_404(Movie, id=movie_id)
    seats = Seat.objects.filter(movie=movie).order_by('seat_number')

    # handles form submission and extracts the seat chosen by the user, their name, and email
    if request.method == "POST":
        seat_id = request.POST.get('seat_id')
        name = request.POST.get('name')
        email = request.POST.get('email')
        amount = float(movie.ticket_price)  

        try:
            # select_for_update() locks the seat row for this transaction to prevent double booking. 
            # If the seat is already booked, it returns an error.
            seat = Seat.objects.select_for_update().get(id=seat_id, movie=movie)

            if seat.is_booked:
                return render(request, 'reservations/seat_selection.html', {
                    'movie': movie,
                    'seats': seats,
                    'error': _('Seat already booked.')
                })

            # temporarily marks the seat as booked in the database before payment
            seat.is_booked = True
            seat.save()

            # creates a reservation record with is_paid=False
            reservation = Reservation.objects.create(
                movie=movie,
                seat=seat,
                user=name,
                email=email,
                is_paid=False
            )

            # ✅ Generate a unique transaction reference with UUID
            tx_ref = f"reservation_{reservation.id}_{uuid.uuid4().hex[:8]}"

            # creates a transaction record linked to the reservation.
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
                "customization[title]": str(_(f"Ticket for {movie.title}")),
                "customization[description]": str(_("Cinema seat booking")),
            }

            headers = {
                "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            chapa_response = requests.post(settings.CHAPA_BASE_URL, json=chapa_data, headers=headers)
            response_data = chapa_response.json()

            # Debugging logs
            print("Chapa Status Code:", chapa_response.status_code)
            print("Chapa Response Data:", response_data)

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
        'seats': seats,
        'ticket_price': movie.ticket_price  # Pass to template
    })

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.shortcuts import render
from io import BytesIO
import qrcode
from .models import Transaction


def payment_success(request):
    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return render(request, "reservations/payment_failed.html", {
            "error": _("Transaction reference missing.")
        })

    url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)  #   timeout
        response.raise_for_status()
        chapa_data = response.json()
    except requests.exceptions.Timeout:
        return render(request, "reservations/payment_failed.html", {
            "error": _("Payment verification timed out. Please try again.")
        })
    except requests.exceptions.RequestException as e:
        return render(request, "reservations/payment_failed.html", {
            "error": _("Could not verify payment: ") + str(e)
        })

    if chapa_data.get("status") != "success":
        return render(request, "reservations/payment_failed.html", {
            "error": _("Payment verification failed.")
        })

    try:
        transaction = Transaction.objects.get(transaction_id=tx_ref)
        reservation = transaction.reservation
    except Transaction.DoesNotExist:
        return render(request, "reservations/payment_failed.html", {
            "error": _("Transaction not found.")
        })

    if not reservation.is_paid:
        reservation.is_paid = True
        reservation.save()

        transaction.status = "success"
        transaction.save()

        #  Generate QR Code
        qr = qrcode.make(_(f"Reservation ID: {reservation.id} - Seat: {reservation.seat.seat_number}"))
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        reservation.qr_code.save(f"qr_{reservation.id}.png", ContentFile(buffer.getvalue()))
        buffer.close()

    #  Send confirmation email (only once)
    if not reservation.email_sent:
        subject = _("🎟 Your Cinema Ticket Confirmation")
        message = _(f"Dear {reservation.user},\n\nYour ticket has been confirmed. "
                    f"Seat: {reservation.seat.seat_number}")

        email_msg = EmailMessage(subject, message, to=[reservation.email])
        if reservation.qr_code:
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
        # Update reservation and transaction
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
                recipient_list=[settings.DEFAULT_FROM_EMAIL], 
                fail_silently=False,
            )

            return render(request, 'reservations/contact.html', {'success': True})
        else:
            messages.error(request, "Please fill in all fields.")

    return render(request, 'reservations/contact.html')

from django.shortcuts import render

def about_view(request):
    return render(request, 'reservations/about.html')


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


