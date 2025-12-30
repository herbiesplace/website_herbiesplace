from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.forms import SignupForm
from django import forms
from django.core.exceptions import ValidationError
from datetime import date
from .models import Profile


class CustomSignupForm(SignupForm):
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        required=True,
        initial=Profile.ROLE_VISITOR,
        help_text="Select your role on the platform",
        widget=forms.Select(attrs={'class': 'textarea'})
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'textarea'}),
        help_text="You must be 18+ to view adult content"
    )
    accept_terms = forms.BooleanField(
        required=True,
        label="I am 18+ and I agree to the Terms & Conditions and content rules",
        help_text="You confirm that you have read the Terms & Conditions and that all models in your uploads are 18+ and have given consent."
    )

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 0:
                raise ValidationError("Date of birth cannot be in the future.")
            if dob > today:
                raise ValidationError("Date of birth cannot be in the future.")
        return dob

    def save(self, request):
        user = super().save(request)
        # Save role and date of birth to profile
        profile = user.profile
        profile.role = self.cleaned_data["role"]
        profile.date_of_birth = self.cleaned_data["date_of_birth"]
        profile.save()
        return user

