from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import MediaContent, MediaRating
from .forms import RatingForm
from django.db.models import Avg

@login_required
def media_list(request):
    media_files = MediaContent.objects.all().order_by('-uploaded_at')
    return render(request, 'streaming/media_list.html', {'media_files': media_files})

@login_required
def media_detail(request, pk):
    media = get_object_or_404(MediaContent, pk=pk)

    # Average rating
    average_rating = MediaRating.objects.filter(video=media).aggregate(Avg('rating'))['rating__avg'] or 0

    # User's previous rating if exists
    user_rating = None
    if request.user.is_authenticated:
        try:
            user_rating = MediaRating.objects.get(user=request.user, video=media).rating
        except MediaRating.DoesNotExist:
            user_rating = None

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            rating_value = form.cleaned_data['rating']
            # Update or create user rating
            MediaRating.objects.update_or_create(
                user=request.user,
                video=media,
                defaults={'rating': rating_value}
            )
            return redirect('streaming:media_detail', pk=pk)
    else:
        form = RatingForm()

    context = {
        'media': media,
        'form': form,
        'average_rating': average_rating,
        'user_rating': user_rating
    }

    return render(request, 'streaming/media_detail.html', context)
