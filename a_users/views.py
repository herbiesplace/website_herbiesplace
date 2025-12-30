from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from allauth.account.utils import send_email_confirmation
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from .forms import *
from .models import FriendRequest, Message, DobChangeRequest, AuditLog
from a_portfolio.models import Photo

def profile_view(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username).profile
    else:
        try:
            profile = request.user.profile
        except:
            return redirect('account_login')
    return render(request, 'a_users/profile.html', {'profile':profile})


@login_required
def profile_edit_view(request):
    form = ProfileForm(instance=request.user.profile, request=request)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile, request=request)
        if form.is_valid():
            profile = form.instance
            old_role = profile.role
            form.save()
            # Audit role change
            if old_role != form.instance.role:
                AuditLog.objects.create(
                    user=request.user,
                    actor=request.user,
                    action=AuditLog.ACTION_PROFILE,
                    field="role",
                    old_value=old_role,
                    new_value=form.instance.role,
                )
            return redirect('profile')
        
    if request.path == reverse('profile-onboarding'):
        onboarding = True
    else:
        onboarding = False
      
    return render(request, 'a_users/profile_edit.html', { 'form':form, 'onboarding':onboarding })


@login_required
def profile_settings_view(request):
    return render(request, 'a_users/profile_settings.html')


@login_required
def dob_change_request_view(request):
    profile = request.user.profile
    if profile.dob_change_pending:
        messages.info(request, "DOB change already requested and pending.")
        return redirect("profile-settings")

    if request.method == "POST":
        form = DobChangeRequestForm(request.POST)
        if form.is_valid():
            dob_req = form.save(commit=False)
            dob_req.user = request.user
            dob_req.status = DobChangeRequest.STATUS_PENDING
            dob_req.save()
            profile.dob_change_pending = True
            profile.save(update_fields=["dob_change_pending"])
            messages.success(request, "DOB change request submitted. Adult content will be blocked until review.")
            return redirect("profile-settings")
    else:
        form = DobChangeRequestForm()

    return render(request, "a_users/dob_change_request.html", {"form": form})


@login_required
def friends_view(request):
    profile = request.user.profile
    # Visitors cannot use connections
    if profile.role == Profile.ROLE_VISITOR:
        return HttpResponseForbidden("Visitors cannot manage connections.")

    q = request.GET.get("q", "").strip()
    friends = profile.friends.select_related("user").all().order_by("displayname", "user__username")

    # Search users (exclude self and existing friends)
    search_results = []
    if q:
        search_results = (
            User.objects.filter(
                Q(username__icontains=q)
                | Q(profile__displayname__icontains=q)
                | Q(email__icontains=q)
            )
            .exclude(id=request.user.id)
            .exclude(profile__role=Profile.ROLE_VISITOR)
            .exclude(id__in=friends.values_list("user_id", flat=True))
            .distinct()
            .select_related("profile")
            .order_by("username")
        )

    # Friend requests
    incoming = (
        FriendRequest.objects.filter(to_user=request.user, status=FriendRequest.STATUS_PENDING)
        .select_related("from_user", "from_user__profile")
        .order_by("-created_at")
    )
    outgoing = (
        FriendRequest.objects.filter(from_user=request.user, status=FriendRequest.STATUS_PENDING)
        .select_related("to_user", "to_user__profile")
        .order_by("-created_at")
    )

    return render(
        request,
        "a_users/friends.html",
        {
            "friends": friends,
            "incoming": incoming,
            "outgoing": outgoing,
            "search_query": q,
            "search_results": search_results,
        },
    )


@login_required
def friend_detail(request, username):
    target_user = get_object_or_404(User.objects.select_related("profile"), username=username)
    if target_user == request.user:
        return redirect("profile")

    # Must be friends
    if not request.user.profile.friends.filter(user=target_user).exists():
        return HttpResponseForbidden("You are not connected with this user.")

    # Photos of target user filtered by visibility relative to the requester
    photos = Photo.objects.filter(owner=target_user)
    viewer_profile = getattr(request.user, "profile", None)
    photos = photos.filter(
        Q(visibility=Photo.VISIBILITY_PUBLIC)
        | Q(visibility=Photo.VISIBILITY_AUTH)
        | Q(
            visibility=Photo.VISIBILITY_FRIENDS,
            allowed_friends__in=[viewer_profile] if viewer_profile else [],
        )
        | Q(owner=request.user)
    ).distinct().select_related("category", "owner", "owner__profile").order_by("-captured_on", "-created_at")

    return render(
        request,
        "a_users/friend_detail.html",
        {
            "target_user": target_user,
            "photos": photos,
        },
    )


@login_required
def message_thread(request, username):
    target_user = get_object_or_404(User.objects.select_related("profile"), username=username)
    if target_user == request.user:
        return redirect("messages")

    # Must be friends
    if not request.user.profile.friends.filter(user=target_user).exists():
        return HttpResponseForbidden("You are not connected with this user.")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            Message.objects.create(sender=request.user, recipient=target_user, content=content)
            return redirect("message-thread", username=target_user.username)

    messages_thread = Message.objects.filter(
        Q(sender=request.user, recipient=target_user) | Q(sender=target_user, recipient=request.user)
    ).select_related("sender__profile", "recipient__profile").order_by("created_at")

    # Mark received messages as read
    Message.objects.filter(sender=target_user, recipient=request.user, is_read=False).update(is_read=True)

    return render(
        request,
        "a_users/message_thread.html",
        {
            "target_user": target_user,
            "messages_thread": messages_thread,
        },
    )


@login_required
def friend_request_send(request, user_id):
    target = get_object_or_404(User, id=user_id)
    profile = request.user.profile
    if profile.role == Profile.ROLE_VISITOR:
        return HttpResponseForbidden("Visitors cannot send friend requests.")
    if target == request.user:
        return HttpResponseForbidden("You cannot send a request to yourself.")
    if profile.friends.filter(user=target).exists():
        return redirect("friends")

    # Avoid duplicate pending in either direction
    fr, created = FriendRequest.objects.get_or_create(
        from_user=request.user, to_user=target,
        defaults={"status": FriendRequest.STATUS_PENDING}
    )
    if not created and fr.status == FriendRequest.STATUS_DECLINED:
        fr.status = FriendRequest.STATUS_PENDING
        fr.save(update_fields=["status"])

    messages.success(request, f"Connection request sent to {target.username}.")
    return redirect("friends")


@login_required
def friend_request_accept(request, request_id):
    fr = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)
    if fr.status != FriendRequest.STATUS_PENDING:
        return redirect("friends")

    # Add to friends (symmetrical M2M)
    fr.to_user.profile.friends.add(fr.from_user.profile)
    fr.status = FriendRequest.STATUS_ACCEPTED
    fr.save(update_fields=["status"])
    messages.success(request, f"You are now connected with {fr.from_user.username}.")
    return redirect("friends")


@login_required
def friend_request_decline(request, request_id):
    fr = get_object_or_404(FriendRequest, id=request_id)
    if fr.to_user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You cannot decline this request.")
    fr.status = FriendRequest.STATUS_DECLINED
    fr.save(update_fields=["status"])
    messages.info(request, "Request declined.")
    return redirect("friends")


@login_required
def messages_view(request):
    """
    Inbox-style view: show conversations (distinct users) with last message and unread counts.
    """
    # Get conversations where the user is sender or recipient
    conversations = (
        Message.objects.filter(Q(sender=request.user) | Q(recipient=request.user))
        .select_related("sender__profile", "recipient__profile")
        .order_by("-created_at")
    )

    threads = {}
    for msg in conversations:
        other = msg.recipient if msg.sender == request.user else msg.sender
        if other.id not in threads:
            threads[other.id] = {
                "user": other,
                "last_message": msg,
                "unread_count": 0,
            }
        # Count unread from other -> current user
        if msg.recipient == request.user and not msg.is_read:
            threads[other.id]["unread_count"] += 1

    # Sort threads by last message time descending
    thread_list = sorted(
        threads.values(), key=lambda t: t["last_message"].created_at, reverse=True
    )

    return render(
        request,
        "a_users/messages.html",
        {"threads": thread_list},
    )


@login_required
def profile_emailchange(request):
    
    if request.htmx:
        form = EmailForm(instance=request.user)
        return render(request, 'partials/email_form.html', {'form':form})
    
    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():
            
            # Check if the email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} is already in use.')
                return redirect('profile-settings')
            
            form.save() 
            
            # Then Signal updates emailaddress and set verified to False
            
            # Then send confirmation email 
            send_email_confirmation(request, request.user)
            
            return redirect('profile-settings')
        else:
            messages.warning(request, 'Form not valid')
            return redirect('profile-settings')
        
    return redirect('home')


@login_required
def profile_emailverify(request):
    send_email_confirmation(request, request.user)
    return redirect('profile-settings')


@login_required
def profile_delete_view(request):
    user = request.user
    if request.method == "POST":
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted, what a pity')
        return redirect('home')
    
    return render(request, 'a_users/profile_delete.html')