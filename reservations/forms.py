#calls forms from django to collect and validate user input.
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, label="Your name")
    email = forms.EmailField(label="Your email")
    subject = forms.CharField(max_length=150)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}), max_length=2000)
    allow_reply = forms.BooleanField(required=False, initial=True, label="Allow us to reply")
