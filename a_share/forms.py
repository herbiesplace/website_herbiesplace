from django import forms

from .models import TransferFile


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class TransferCreateForm(forms.Form):
    recipient_email = forms.EmailField(
        label="Recipient email",
        widget=forms.EmailInput(attrs={"class": "textarea", "placeholder": "email@example.com"}),
    )
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "textarea", "placeholder": "Optional title for this transfer"}),
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": "textarea",
                "placeholder": "Optional message to include in the email",
            }
        ),
    )
    files = forms.Field(
        widget=MultipleFileInput(
            attrs={
                "id": "id_files",
                "multiple": True,
                "accept": "*/*",
                "class": "sr-only",
            }
        ),
        required=False,
    )

    def clean_files(self):
        files = self.files.getlist("files")
        if not files:
            raise forms.ValidationError("Please select at least one file.")
        return files


class CodeOnlyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="6‑digit code",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )


class EmailCodeForm(CodeOnlyForm):
    email = forms.EmailField(
        label="Your email address",
        widget=forms.EmailInput(attrs={"class": "textarea", "placeholder": "email@example.com"}),
    )


