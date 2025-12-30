from django import forms
from django.forms import ModelForm
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import Category, Photo
from a_users.models import Profile


def validate_image_size(image):
    """Validate that uploaded image is not too large"""
    max_size = getattr(settings, 'MAX_PHOTO_SIZE', 10 * 1024 * 1024)  # Default 10 MB
    if image.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'Image file too large. Maximum size is {max_size_mb:.0f} MB.'
        )


class CategoryForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        if not (self.request and self.request.user and self.request.user.is_staff):
            # Only staff can change is_adult_only; show but disable for others
            if "is_adult_only" in self.fields:
                self.fields["is_adult_only"].disabled = True

    class Meta:
        model = Category
        fields = ["name", "is_adult_only"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Category name"}),
            "is_adult_only": forms.CheckboxInput(),
        }
        help_texts = {
            "is_adult_only": "Only visible to users 18+ who have adult content enabled. Staff only.",
        }


class CommentForm(forms.Form):
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Write a comment..."}),
    )
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())


class PhotoForm(ModelForm):
    class Meta:
        model = Photo
        fields = [
            "title",
            "description",
            "image",
            "captured_on",
            "category",
            "visibility",
            "allowed_friends",
        ]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*", "class": "block"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "captured_on": forms.DateInput(attrs={"type": "date"}),
            "allowed_friends": forms.SelectMultiple(attrs={"size": 6}),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            validate_image_size(image)
        return image


class MultipleFileInput(forms.ClearableFileInput):
    """
    Widget that allows selecting multiple image files.
    """

    allow_multiple_selected = True


class MultiPhotoUploadForm(forms.Form):
    title = forms.CharField(max_length=140)
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    images = forms.Field(
        widget=MultipleFileInput(
            attrs={
                "multiple": True,
                "accept": "image/*",
                "class": "block",
            }
        ),
        required=False,
    )
    captured_on = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
    )
    visibility = forms.ChoiceField(
        choices=Photo.VISIBILITY_CHOICES,
        initial=Photo.VISIBILITY_PUBLIC,
    )
    allowed_friends = forms.ModelMultipleChoiceField(
        queryset=Profile.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "profile"):
            self.fields["allowed_friends"].queryset = user.profile.friends.all()
        else:
            self.fields["allowed_friends"].queryset = Profile.objects.none()

    def clean_images(self):
        files = self.files.getlist("images")
        if not files:
            raise ValidationError("Please select at least one image.")
        for f in files:
            validate_image_size(f)
        return files

