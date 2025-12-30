from django import forms


class ContactForm(forms.Form):
    REASON_SUPPORT = "support"
    REASON_LOGIN = "login"
    REASON_INFO = "info"
    REASON_OTHER = "other"
    
    REASON_CHOICES = [
        (REASON_SUPPORT, "Support"),
        (REASON_LOGIN, "Not able to login"),
        (REASON_INFO, "General information"),
        (REASON_OTHER, "Other"),
    ]
    
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Your name"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "your.email@example.com"}),
    )
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        required=True,
        widget=forms.Select(),
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Your message..."}),
    )
    # Honeypot field for bot protection (hidden from users)
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"style": "display: none;", "tabindex": "-1", "autocomplete": "off"}),
        label="",
    )
    
    def clean_website(self):
        """If this field is filled, it's likely a bot"""
        website = self.cleaned_data.get("website")
        if website:
            raise forms.ValidationError("Bot detected.")
        return website

