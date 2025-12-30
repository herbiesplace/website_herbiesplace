from django.forms import ModelForm
from django import forms
from django.contrib.auth.models import User
from .models import Profile, DobChangeRequest

class ProfileForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if not (self.request and self.request.user and self.request.user.is_staff):
            # Only staff can change role; show but disable for others
            self.fields["role"].disabled = True
        # Only show adult content preference if user is 18+
        if self.instance and self.instance.pk:
            if not self.instance.is_adult:
                self.fields["show_adult_content"].widget = forms.HiddenInput()
            # Lock DOB for non-staff once set
            if self.instance.date_of_birth and not (self.request and self.request.user and self.request.user.is_staff):
                self.fields["date_of_birth"].disabled = True

    class Meta:
        model = Profile
        fields = ['image', 'displayname', 'info', 'role', 'date_of_birth', 'show_adult_content']
        widgets = {
            'image': forms.FileInput(),
            'displayname' : forms.TextInput(attrs={'placeholder': 'Add display name'}),
            'info' : forms.Textarea(attrs={'rows':3, 'placeholder': 'Add information'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'show_adult_content': forms.CheckboxInput(),
        }
        help_texts = {
            'date_of_birth': 'Required for age verification',
            'show_adult_content': 'Show adult-only content (only applies if you are 18+)',
        }
        
        
class EmailForm(ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['email']


class DobChangeRequestForm(forms.ModelForm):
    class Meta:
        model = DobChangeRequest
        fields = ["requested_dob", "note"]
        widgets = {
            "requested_dob": forms.DateInput(attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
        }
