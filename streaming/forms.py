from django import forms
from .models import StreamingSubscription

class StreamingSubscriptionForm(forms.ModelForm):
    class Meta:
        model = StreamingSubscription
        fields = ['full_name', 'email', 'subscription_type']
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    plan = forms.ChoiceField(choices=[('monthly', 'Monthly'), ('annual', 'Annual')], required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "plan")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email address already in use.")
        return email

from django import forms
from .models import UserProfile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']

