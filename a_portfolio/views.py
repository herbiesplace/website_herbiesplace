from io import BytesIO
import os

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from django.core.files.base import ContentFile
from PIL import Image

from .forms import CategoryForm, PhotoForm, CommentForm, MultiPhotoUploadForm
from .models import Category, Photo, Like, Comment
from a_users.models import Profile
from a_users.models import Profile


def _resize_shortest_side(file_obj, target: int = 1920) -> ContentFile:
    """
    Resize an image so that its shortest side is `target` pixels,
    keeping aspect ratio. Returns a ContentFile ready to be saved.
    """
    img = Image.open(file_obj)
    img = img.convert("RGB")

    width, height = img.size
    shortest = min(width, height)

    if shortest == target:
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return ContentFile(buffer.read())

    scale = target / shortest
    new_size = (int(width * scale), int(height * scale))
    img = img.resize(new_size, Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    return ContentFile(buffer.read())


def _user_can_upload(user):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.can_upload_portfolio)


def _filter_photos_for_user(user):
    """
    Build queryset with visibility rules:
    - Public: always visible
    - Authenticated: visible to logged-in users
    - Friends: visible to owner or if user is in allowed_friends
    - Adult-only: filtered based on user age and preferences
    """
    public_qs = Photo.objects.filter(visibility=Photo.VISIBILITY_PUBLIC)
    if not user.is_authenticated:
        # Non-authenticated users: only public, non-adult photos
        return public_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        ).select_related("category", "owner", "owner__profile")

    profile = getattr(user, "profile", None)
    can_view_adult = profile and profile.can_view_adult_content if profile else False
    
    auth_qs = Photo.objects.filter(visibility=Photo.VISIBILITY_AUTH)
    friends_qs = Photo.objects.filter(visibility=Photo.VISIBILITY_FRIENDS).filter(
        allowed_friends__in=[profile] if profile else []
    )
    own_qs = Photo.objects.filter(owner=user)
    
    # Filter adult-only content
    if not can_view_adult:
        # Exclude photos in adult-only categories
        public_qs = public_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
        auth_qs = auth_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
        friends_qs = friends_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
        # Owners can always see their own photos, but we filter for consistency
    
    return (
        public_qs
        | auth_qs
        | friends_qs
        | own_qs
    ).distinct().select_related("category", "owner", "owner__profile")


def portfolio_list(request):
    category_slug = request.GET.get("category")
    photos = _filter_photos_for_user(request.user)
    selected_category = None
    requires_login = False
    
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        photos = photos.filter(category=selected_category)
        
        # Check if category has photos that require authentication but user is not logged in
        if not request.user.is_authenticated:
            # Check if this category has any photos that are not public
            has_non_public_photos = Photo.objects.filter(
                category=selected_category
            ).exclude(visibility=Photo.VISIBILITY_PUBLIC).exists()
            
            # Check if there are any public photos in this category
            has_public_photos = Photo.objects.filter(
                category=selected_category,
                visibility=Photo.VISIBILITY_PUBLIC
            ).filter(
                models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
            ).exists()
            
            # If category has non-public photos but no public photos (or filtered out), require login
            if has_non_public_photos and not has_public_photos and photos.count() == 0:
                requires_login = True

    categories = Category.objects.all()
    return render(
        request,
        "a_portfolio/gallery.html",
        {
            "photos": photos,
            "categories": categories,
            "selected_category": selected_category,
            "requires_login": requires_login,
        },
    )


@login_required
def my_portfolio(request):
    """
    Personal landing page for photographers / models / MUAs (and staff)
    showing all photos they have uploaded.
    """
    if not _user_can_upload(request.user):
        return HttpResponseForbidden(
            "Your role cannot access a personal portfolio. Only photographers, models, makeup artists, and staff can view this page."
        )

    photos = (
        Photo.objects.filter(owner=request.user)
        .select_related("category", "owner", "owner__profile")
        .order_by("-captured_on", "-created_at")
    )

    return render(
        request,
        "a_portfolio/my_portfolio.html",
        {"photos": photos},
    )


def user_portfolio(request, username):
    """
    Public link to a user's portfolio using their username.
    - If viewing your own: show all your photos.
    - If viewing another user: show only what _filter_photos_for_user allows and scoped to that owner.
    """
    target_user = get_object_or_404(User.objects.select_related("profile"), username=username)

    if request.user.is_authenticated and request.user == target_user:
        photos = (
            Photo.objects.filter(owner=target_user)
            .select_related("category", "owner", "owner__profile")
            .order_by("-captured_on", "-created_at")
        )
    else:
        photos = (
            _filter_photos_for_user(request.user)
            .filter(owner=target_user)
            .order_by("-captured_on", "-created_at")
        )

    return render(
        request,
        "a_portfolio/user_portfolio.html",
        {"photos": photos, "target_user": target_user},
    )


@login_required
def portfolio_private(request):
    categories = Category.objects.all()
    profile = getattr(request.user, "profile", None)
    can_view_adult = profile and profile.can_view_adult_content if profile else False

    auth_qs = Photo.objects.filter(visibility=Photo.VISIBILITY_AUTH)
    friends_qs = Photo.objects.filter(
        visibility=Photo.VISIBILITY_FRIENDS,
        allowed_friends__in=[profile] if profile else []
    )
    # Only your non-public photos in this private view
    own_qs = Photo.objects.filter(owner=request.user).exclude(visibility=Photo.VISIBILITY_PUBLIC)

    # Filter adult-only content
    if not can_view_adult:
        auth_qs = auth_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
        friends_qs = friends_qs.filter(
            models.Q(category__isnull=True) | models.Q(category__is_adult_only=False)
        )
        # Owners can always see their own photos

    photos = (auth_qs | friends_qs | own_qs).distinct().select_related("category", "owner", "owner__profile")
    return render(
        request,
        "a_portfolio/gallery_private.html",
        {"photos": photos, "categories": categories},
    )


def photo_detail(request, pk):
    photo = get_object_or_404(
        Photo.objects.select_related("category", "owner", "owner__profile"), pk=pk
    )
    
    # Check adult-only content restriction
    if photo.category and photo.category.is_adult_only:
        if not request.user.is_authenticated:
            return HttpResponseForbidden("You must be logged in and 18+ to view this content.")
        profile = getattr(request.user, "profile", None)
        if not (profile and profile.can_view_adult_content):
            return HttpResponseForbidden("This content is restricted to users 18+ who have adult content enabled in their profile settings.")
    
    allowed = photo.visibility == Photo.VISIBILITY_PUBLIC
    if request.user.is_authenticated:
        if photo.owner == request.user:
            allowed = True
        elif photo.visibility == Photo.VISIBILITY_AUTH:
            allowed = True
        elif (
            photo.visibility == Photo.VISIBILITY_FRIENDS
            and getattr(request.user, "profile", None)
            in photo.allowed_friends.all()
        ):
            allowed = True
    if not allowed:
        return HttpResponseForbidden("You do not have access to this photo.")

    comments = photo.comments.filter(parent=None).select_related("user", "user__profile")
    is_liked = False
    if request.user.is_authenticated:
        is_liked = photo.is_liked_by(request.user)

    return render(
        request,
        "a_portfolio/photo_detail.html",
        {
            "photo": photo,
            "comments": comments,
            "is_liked": is_liked,
            "comment_form": CommentForm(),
        },
    )


@login_required
def photo_create(request):
    if not _user_can_upload(request.user):
        return HttpResponseForbidden("Your role cannot upload photos.")
    if request.method == "POST":
        form = MultiPhotoUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            images = form.cleaned_data["images"]
            uploaded_count = 0
            for image_file in images:
                photo = Photo(
                    owner=request.user,
                    title=form.cleaned_data["title"],
                    description=form.cleaned_data.get("description", ""),
                    captured_on=form.cleaned_data.get("captured_on"),
                    category=form.cleaned_data.get("category"),
                    visibility=form.cleaned_data.get("visibility", Photo.VISIBILITY_PUBLIC),
                )
                photo.save()

                processed = _resize_shortest_side(image_file, target=1920)
                base_name, _ext = os.path.splitext(image_file.name)
                filename = f"{base_name}_1920.jpg"
                photo.image.save(filename, processed, save=True)

                allowed_friends = form.cleaned_data.get("allowed_friends")
                if allowed_friends:
                    photo.allowed_friends.set(allowed_friends)
                
                uploaded_count += 1

            messages.success(
                request,
                f"Successfully uploaded {uploaded_count} image{'' if uploaded_count == 1 else 's'}!"
            )

            if request.htmx:
                # Return a redirect response for HTMX
                from django.http import HttpResponse
                response = HttpResponse()
                response["HX-Redirect"] = "/portfolio/"
                return response
            return redirect("portfolio")
    else:
        form = MultiPhotoUploadForm(user=request.user)
    template = (
        "a_portfolio/partials/photo_form.html"
        if request.htmx
        else "a_portfolio/photo_form_page.html"
    )
    return render(request, template, {"form": form})


@login_required
def photo_update(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if photo.owner != request.user:
        return HttpResponseForbidden("You do not have permission to edit this photo.")
    if not _user_can_upload(request.user):
        return HttpResponseForbidden("Your role cannot edit photos.")

    if request.method == "POST":
        form = PhotoForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            old_visibility = photo.visibility
            form.save()
            new_visibility = form.instance.visibility
            if old_visibility != new_visibility:
                AuditLog.objects.create(
                    user=photo.owner,
                    actor=request.user,
                    action=AuditLog.ACTION_PHOTO,
                    field="visibility",
                    old_value=old_visibility,
                    new_value=new_visibility,
                )
            return redirect("portfolio-detail", pk=photo.pk)
    else:
        form = PhotoForm(instance=photo)

    template = (
        "a_portfolio/partials/photo_form.html"
        if request.htmx
        else "a_portfolio/photo_form_page.html"
    )
    return render(request, template, {"form": form, "photo": photo})


@login_required
def photo_bulk_delete(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request.")

    ids = request.POST.getlist("photo_ids")
    if not ids:
        return redirect(request.META.get("HTTP_REFERER", "portfolio-mine"))

    qs = Photo.objects.filter(pk__in=ids)
    if not request.user.is_staff:
        qs = qs.filter(owner=request.user)

    qs.delete()
    return redirect(request.META.get("HTTP_REFERER", "portfolio-mine"))


@login_required
def photo_delete(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if photo.owner != request.user:
        return HttpResponseForbidden("You do not have permission to delete this photo.")
    if not _user_can_upload(request.user):
        return HttpResponseForbidden("Your role cannot delete photos.")

    if request.method == "POST":
        photo.delete()
        return redirect("portfolio")

    return render(
        request,
        "a_portfolio/photo_delete_confirm.html",
        {"photo": photo},
    )


@login_required
def category_create(request):
    # Only users who can upload (photographer, model, mua) or staff can create categories
    # Visitors cannot create categories
    if not _user_can_upload(request.user):
        return HttpResponseForbidden("Your role cannot create categories. Only photographers, models, makeup artists, and staff can create categories.")
    
    if request.method == "POST":
        form = CategoryForm(request.POST, request=request)
        if form.is_valid():
            form.save()
            if request.htmx:
                categories = Category.objects.all()
                return render(
                    request,
                    "a_portfolio/partials/category_options.html",
                    {"categories": categories},
                )
            return redirect("portfolio")
    else:
        form = CategoryForm(request=request)
    template = (
        "a_portfolio/partials/category_form.html"
        if request.htmx
        else "a_portfolio/category_form_page.html"
    )
    return render(request, template, {"form": form})


@login_required
def photo_like(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    like, created = Like.objects.get_or_create(photo=photo, user=request.user)
    
    if not created:
        like.delete()
        is_liked = False
    else:
        is_liked = True
    
    if request.htmx:
        return render(
            request,
            "a_portfolio/partials/like_button.html",
            {"photo": photo, "is_liked": is_liked},
        )
    return redirect("portfolio-detail", pk=pk)


@login_required
def comment_create(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            parent_id = form.cleaned_data.get("parent_id")
            parent = None
            if parent_id:
                parent = get_object_or_404(Comment, pk=parent_id, photo=photo)
            
            comment = Comment.objects.create(
                photo=photo,
                user=request.user,
                content=form.cleaned_data["content"],
                parent=parent,
            )
            
            if request.htmx:
                if parent:
                    # Return updated replies
                    return render(
                        request,
                        "a_portfolio/partials/comment_replies.html",
                        {"comment": parent, "photo": photo},
                    )
                else:
                    # Return updated comment list
                    comments = photo.comments.filter(parent=None).select_related("user", "user__profile")
                    return render(
                        request,
                        "a_portfolio/partials/comment_list.html",
                        {"comments": comments, "photo": photo},
                    )
            return redirect("portfolio-detail", pk=pk)
    
    return redirect("portfolio-detail", pk=pk)


@login_required
def comment_delete(request, pk, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    photo = comment.photo
    
    # Only owner of photo, comment author, or staff can delete
    can_delete = (
        comment.user == request.user
        or photo.owner == request.user
        or request.user.is_staff
    )
    
    if not can_delete:
        return HttpResponseForbidden("You cannot delete this comment.")
    
    comment.delete()
    
    if request.htmx:
        comments = photo.comments.filter(parent=None).select_related("user", "user__profile")
        return render(
            request,
            "a_portfolio/partials/comment_list.html",
            {"comments": comments, "photo": photo},
        )
    return redirect("portfolio-detail", pk=pk)