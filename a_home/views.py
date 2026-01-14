from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from a_portfolio.models import Photo, Category
from a_portfolio.views import _filter_photos_for_user
from .forms import ContactForm


def home_view(request):
    public_photos = Photo.objects.filter(
        visibility=Photo.VISIBILITY_PUBLIC
    )
    
    # Filter adult-only content based on user
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        can_view_adult = profile and profile.can_view_adult_content if profile else False
        if not can_view_adult:
            public_photos = public_photos.filter(
                models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
            )
    else:
        # Non-authenticated: no adult content
        public_photos = public_photos.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
    
    public_photos = public_photos.order_by("-captured_on", "-created_at")[:10]
    return render(request, "home.html", {"public_photos": public_photos})


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            reason = dict(form.fields['reason'].choices)[form.cleaned_data['reason']]
            message = form.cleaned_data['message']
            
            # Send email
            subject = f"Contact Form: {reason} - {name}"
            email_message = f"""
You have received a new contact form submission:

Name: {name}
Email: {email}
Reason: {reason}

Message:
{message}

---
This email was sent from the portfolio website contact form.
"""
            try:
                send_mail(
                    subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ['herbiesplace@outlook.be'],
                    fail_silently=False,
                )
                messages.success(request, 'Thank you! Your message has been sent successfully.')
                return redirect('contact')
            except Exception as e:
                # Log the error for debugging (in production, use proper logging)
                import traceback
                print(f"Email error: {e}")
                traceback.print_exc()
                messages.error(request, f'Sorry, there was an error sending your message: {str(e)}. Please try again later.')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})


def search_view(request):
    q = request.GET.get("q", "").strip()
    photos = []
    categories = []
    users = []

    if q:
        # Photos respecting visibility
        photos = (
            _filter_photos_for_user(request.user)
            .filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__name__icontains=q)
            )
            .order_by("-captured_on", "-created_at")[:30]
        )

        # Categories (respect adult visibility)
        categories_qs = Category.objects.filter(name__icontains=q)
        profile = getattr(request.user, "profile", None)
        can_view_adult = profile and profile.can_view_adult_content if profile else False
        if not can_view_adult:
            categories_qs = categories_qs.filter(is_adult_only=False)
        categories = categories_qs.order_by("name")[:20]

        # Users
        users = (
            User.objects.select_related("profile")
            .filter(
                Q(username__icontains=q)
                | Q(profile__displayname__icontains=q)
                | Q(email__icontains=q)
            )
            .order_by("username")[:20]
        )

    return render(
        request,
        "search.html",
        {"query": q, "photos": photos, "categories": categories, "users": users},
    )


def trust_safety_view(request):
    """Trust & Safety page explaining content policies, moderation, and data handling."""
    return render(request, "trust_safety.html")


def terms_view(request):
    """
    General terms & conditions and content posting rules.
    This is a static informational page, not a legal document.
    """
    return render(request, "terms.html")
