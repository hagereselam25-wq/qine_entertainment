# views.py
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMessage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Movie, Seat, Reservation, Rating

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

# Seat selection page
def seat_selection(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    seats = Seat.objects.filter(movie=movie).order_by('seat_number')

    if request.method == "POST":
        seat_id = request.POST.get('seat_id')
        name = request.POST.get('name')
        email = request.POST.get('email')

        try:
            seat = Seat.objects.get(id=seat_id, movie=movie)

            if seat.is_booked:
                return render(request, 'reservations/seat_selection.html', {
                    'movie': movie,
                    'seats': seats,
                    'error': 'This seat is already booked. Please select another seat.'
                })

            seat.is_booked = True
            seat.save()

            reservation = Reservation.objects.create(
                movie=movie,
                user=name,
                seat=seat,
                email=email
            )

            qr_data = f"Reservation ID: {reservation.id} | Movie: {movie.title} | Seat: {seat.seat_number} | Name: {name} | Email: {email}"
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer)
            filename = f'reservation_{reservation.id}.png'

            if hasattr(reservation, 'qr_code'):
                reservation.qr_code.save(filename, ContentFile(buffer.getvalue()))

            email_subject = 'Your Movie Ticket Confirmation'
            email_body = (
                f"Hello {name},\n\n"
                f"Your reservation is confirmed!\n\n"
                f"Movie: {movie.title}\n"
                f"Seat: {seat.seat_number}\n"
                f"Show Time: {movie.show_time}\n\n"
                f"View your ticket: http://127.0.0.1:8000/ticket/{reservation.id}\n\n"
                f"Thanks for booking with us!"
            )

            message = EmailMessage(
                subject=email_subject,
                body=email_body,
                from_email=None,
                to=[email],
            )
            message.attach(filename, buffer.getvalue(), 'image/png')
            message.send(fail_silently=False)
            buffer.close()

            return redirect('ticket_confirmation', ticket_id=reservation.id)

        except Seat.DoesNotExist:
            return render(request, 'reservations/seat_selection.html', {
                'movie': movie,
                'seats': seats,
                'error': 'This seat does not exist. Please select a valid seat.'
            })

    return render(request, 'reservations/seat_selection.html', {
        'movie': movie,
        'seats': seats
    })

# Ticket confirmation page
def ticket_confirmation(request, ticket_id):
    reservation = get_object_or_404(Reservation, id=ticket_id)
    return render(request, 'reservations/ticket_confirmation.html', {
        'reservation': reservation
    })

# Payment pages
def payment_success(request):
    return render(request, 'reservations/payment_success.html')

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

# User login view
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
    return render(request, 'reservations/user_login.html')

# User signup view
def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('home')
    return render(request, 'reservations/user_signup.html')

# User logout view
def user_logout(request):
    logout(request)
    return redirect('home')
