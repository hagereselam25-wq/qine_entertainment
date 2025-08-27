from django import forms
from django.utils.translation import gettext_lazy as _
from .models import StreamingSubscription, UserProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# ------------------- Streaming Subscription Form -------------------
class StreamingSubscriptionForm(forms.ModelForm):
    class Meta:
        model = StreamingSubscription
        fields = ['full_name', 'email', 'subscription_type']
        labels = {
            'full_name': _('Full Name'),
            'email': _('Email'),
            'subscription_type': _('Subscription Type'),
        }

from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
from django.utils.translation import gettext_lazy as _

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User

class CustomUserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_("Email"))
    plan = forms.ChoiceField(
        choices=[('monthly', _('Monthly')), ('annual', _('Annual'))],
        required=True,
        label=_("Subscription Plan")
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "plan")
        labels = {
            'username': _('Username'),
            'password1': _('Password'),
            'password2': _('Confirm Password'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Email address already in use."))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Save country in UserProfile
            UserProfile.objects.create(
                user=user,
                country=self.cleaned_data['country']
            )
        return user
# ------------------- Profile Update Form -------------------
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']
        labels = {
            'profile_picture': _('Profile Picture'),
            'bio': _('Bio'),
        }


# forms.py
from django import forms
from .models import StreamingRating

class RatingForm(forms.ModelForm):
    class Meta:
        model = StreamingRating
        fields = ['rating']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5})
        }
