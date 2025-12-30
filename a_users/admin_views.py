from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib import messages

from .models import Profile, DobChangeRequest, AuditLog
from .forms import ProfileForm
from a_portfolio.models import Photo, Category, Comment
from a_portfolio.forms import PhotoForm, CategoryForm


def staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(staff_required)
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    total_users = User.objects.count()
    total_photos = Photo.objects.count()
    total_categories = Category.objects.count()
    total_comments = Comment.objects.count()
    
    # Active users (logged in within last 15 minutes)
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    active_user_ids = [int(session.get_decoded().get("_auth_user_id")) for session in active_sessions if session.get_decoded().get("_auth_user_id")]
    active_users = User.objects.filter(id__in=active_user_ids).distinct()
    
    # Role statistics
    role_stats = Profile.objects.values("role").annotate(count=Count("id"))
    
    # Recent photos
    recent_photos = Photo.objects.select_related("owner", "owner__profile", "category").order_by("-created_at")[:10]
    
    # Recent users
    recent_users = User.objects.select_related("profile").order_by("-date_joined")[:10]
    
    return render(
        request,
        "a_users/admin/dashboard.html",
        {
            "total_users": total_users,
            "total_photos": total_photos,
            "total_categories": total_categories,
            "total_comments": total_comments,
            "active_users": active_users,
            "active_count": active_users.count(),
            "role_stats": role_stats,
            "recent_photos": recent_photos,
            "recent_users": recent_users,
        },
    )


@user_passes_test(staff_required)
def admin_users(request):
    """List and manage all users"""
    search = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    
    users = User.objects.select_related("profile").all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(profile__displayname__icontains=search)
        )
    
    if role_filter:
        users = users.filter(profile__role=role_filter)
    
    users = users.order_by("-date_joined")
    
    return render(
        request,
        "a_users/admin/users.html",
        {
            "users": users,
            "search": search,
            "role_filter": role_filter,
            "role_choices": Profile.ROLE_CHOICES,
        },
    )


@user_passes_test(staff_required)
def admin_user_edit(request, user_id):
    """Edit user and their profile"""
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, request=request)
        if form.is_valid():
            old_role = profile.role
            form.save()
            if old_role != profile.role:
                AuditLog.objects.create(
                    user=user,
                    actor=request.user,
                    action=AuditLog.ACTION_PROFILE,
                    field="role",
                    old_value=old_role,
                    new_value=profile.role,
                )
            messages.success(request, f"Profile for {user.username} updated successfully.")
            return redirect("admin-users")
    else:
        form = ProfileForm(instance=profile, request=request)
    
    return render(
        request,
        "a_users/admin/user_edit.html",
        {"user": user, "profile": profile, "form": form},
    )


@user_passes_test(staff_required)
def admin_user_delete(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        username = user.username
        user.delete()
        messages.success(request, f"User {username} deleted successfully.")
        return redirect("admin-users")
    
    return render(request, "a_users/admin/user_delete.html", {"user": user})


@user_passes_test(staff_required)
def admin_photos(request):
    """List and manage all photos"""
    search = request.GET.get("search", "")
    owner_filter = request.GET.get("owner", "")
    category_filter = request.GET.get("category", "")
    visibility_filter = request.GET.get("visibility", "")
    
    photos = Photo.objects.select_related("owner", "owner__profile", "category").all()
    
    if search:
        photos = photos.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    
    if owner_filter:
        photos = photos.filter(owner__username=owner_filter)
    
    if category_filter:
        photos = photos.filter(category__slug=category_filter)
    
    if visibility_filter:
        photos = photos.filter(visibility=visibility_filter)
    
    photos = photos.order_by("-created_at")
    
    # Get unique owners and categories for filters
    owners = User.objects.filter(photos__isnull=False).distinct().order_by("username")
    categories = Category.objects.filter(photos__isnull=False).distinct().order_by("name")
    
    return render(
        request,
        "a_users/admin/photos.html",
        {
            "photos": photos,
            "search": search,
            "owner_filter": owner_filter,
            "category_filter": category_filter,
            "visibility_filter": visibility_filter,
            "owners": owners,
            "categories": categories,
            "visibility_choices": Photo.VISIBILITY_CHOICES,
        },
    )


@user_passes_test(staff_required)
def admin_photo_edit(request, photo_id):
    """Edit any photo"""
    photo = get_object_or_404(Photo.objects.select_related("owner", "category"), id=photo_id)
    
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
            messages.success(request, f"Photo '{photo.title}' updated successfully.")
            return redirect("admin-photos")
    else:
        form = PhotoForm(instance=photo)
    
    return render(
        request,
        "a_users/admin/photo_edit.html",
        {"photo": photo, "form": form},
    )


@user_passes_test(staff_required)
def admin_photo_delete(request, photo_id):
    """Delete any photo"""
    photo = get_object_or_404(Photo, id=photo_id)
    
    if request.method == "POST":
        title = photo.title
        photo.delete()
        messages.success(request, f"Photo '{title}' deleted successfully.")
        return redirect("admin-photos")
    
    return render(request, "a_users/admin/photo_delete.html", {"photo": photo})


@user_passes_test(staff_required)
def admin_dob_requests(request):
    pending = DobChangeRequest.objects.select_related("user", "user__profile").filter(
        status=DobChangeRequest.STATUS_PENDING
    )
    resolved = DobChangeRequest.objects.select_related("user", "user__profile").exclude(
        status=DobChangeRequest.STATUS_PENDING
    )[:50]
    return render(
        request,
        "a_users/admin/dob_requests.html",
        {"pending": pending, "resolved": resolved},
    )


@user_passes_test(staff_required)
def admin_dob_request_resolve(request, req_id, decision):
    dob_req = get_object_or_404(DobChangeRequest.objects.select_related("user", "user__profile"), id=req_id)
    if dob_req.status != DobChangeRequest.STATUS_PENDING:
        return redirect("admin-dob-requests")

    if request.method == "POST":
        if decision == "approve":
            old_dob = dob_req.user.profile.date_of_birth
            dob_req.user.profile.date_of_birth = dob_req.requested_dob
            dob_req.user.profile.dob_change_pending = False
            dob_req.user.profile.save(update_fields=["date_of_birth", "dob_change_pending"])
            dob_req.status = DobChangeRequest.STATUS_APPROVED
            dob_req.resolved_by = request.user
            dob_req.resolved_at = timezone.now()
            dob_req.save(update_fields=["status", "resolved_by", "resolved_at"])
            AuditLog.objects.create(
                user=dob_req.user,
                actor=request.user,
                action=AuditLog.ACTION_PROFILE,
                field="date_of_birth",
                old_value=str(old_dob) if old_dob else "",
                new_value=str(dob_req.requested_dob),
            )
            messages.success(request, f"DOB updated for {dob_req.user.username}.")
        elif decision == "decline":
            dob_req.status = DobChangeRequest.STATUS_DECLINED
            dob_req.resolved_by = request.user
            dob_req.resolved_at = timezone.now()
            dob_req.save(update_fields=["status", "resolved_by", "resolved_at"])
            dob_req.user.profile.dob_change_pending = False
            dob_req.user.profile.save(update_fields=["dob_change_pending"])
            messages.info(request, f"DOB change declined for {dob_req.user.username}.")
        return redirect("admin-dob-requests")

    return render(
        request,
        "a_users/admin/dob_request_resolve.html",
        {"dob_req": dob_req, "decision": decision},
    )


@user_passes_test(staff_required)
def admin_photos_bulk_delete(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid request.")
    ids = request.POST.getlist("photo_ids")
    if ids:
        Photo.objects.filter(pk__in=ids).delete()
        messages.success(request, "Selected photos deleted.")
    return redirect("admin-photos")


@user_passes_test(staff_required)
def admin_comments(request):
    """List and manage all comments"""
    search = request.GET.get("search", "")
    photo_filter = request.GET.get("photo", "")
    user_filter = request.GET.get("user", "")
    
    comments = Comment.objects.select_related("photo", "photo__owner", "user", "user__profile", "parent").all()
    
    if search:
        comments = comments.filter(content__icontains=search)
    
    if photo_filter:
        comments = comments.filter(photo__id=photo_filter)
    
    if user_filter:
        comments = comments.filter(user__username=user_filter)
    
    comments = comments.order_by("-created_at")
    
    # Get unique photos and users for filters
    photos_with_comments = Photo.objects.filter(comments__isnull=False).distinct().order_by("title")
    users_with_comments = User.objects.filter(photo_comments__isnull=False).distinct().order_by("username")
    
    return render(
        request,
        "a_users/admin/comments.html",
        {
            "comments": comments,
            "search": search,
            "photo_filter": photo_filter,
            "user_filter": user_filter,
            "photos": photos_with_comments,
            "users": users_with_comments,
        },
    )


@user_passes_test(staff_required)
def admin_comment_delete(request, comment_id):
    """Delete any comment"""
    comment = get_object_or_404(Comment.objects.select_related("photo"), pk=comment_id)
    photo = comment.photo
    
    if request.method == "POST":
        comment.delete()
        messages.success(request, "Comment deleted successfully.")
        return redirect("admin-comments")
    
    return render(request, "a_users/admin/comment_delete.html", {"comment": comment, "photo": photo})


@user_passes_test(staff_required)
def admin_categories(request):
    """List and manage all categories"""
    search = request.GET.get("search", "")
    adult_filter = request.GET.get("adult_only", "")
    
    categories = Category.objects.annotate(photo_count=Count("photos")).all()
    
    if search:
        categories = categories.filter(name__icontains=search)
    
    if adult_filter == "yes":
        categories = categories.filter(is_adult_only=True)
    elif adult_filter == "no":
        categories = categories.filter(is_adult_only=False)
    
    categories = categories.order_by("name")
    
    return render(
        request,
        "a_users/admin/categories.html",
        {
            "categories": categories,
            "search": search,
            "adult_filter": adult_filter,
        },
    )


@user_passes_test(staff_required)
def admin_category_edit(request, category_id):
    """Edit a category (including adult-only setting)"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category, request=request)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect("admin-categories")
    else:
        form = CategoryForm(instance=category, request=request)
    
    return render(
        request,
        "a_users/admin/category_edit.html",
        {"category": category, "form": form},
    )


@user_passes_test(staff_required)
def admin_category_delete(request, category_id):
    """Delete a category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == "POST":
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted successfully.")
        return redirect("admin-categories")
    
    return render(request, "a_users/admin/category_delete.html", {"category": category})

