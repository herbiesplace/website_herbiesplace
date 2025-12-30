from .models import Message, FriendRequest, DobChangeRequest


def unread_messages(request):
    if not request.user.is_authenticated:
        return {
            "unread_messages_count": 0,
            "pending_friend_requests_count": 0,
            "pending_dob_requests_count": 0,
        }

    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    pending_requests = FriendRequest.objects.filter(
        to_user=request.user, status=FriendRequest.STATUS_PENDING
    ).count()
    pending_dob = 0
    if request.user.is_staff:
        pending_dob = DobChangeRequest.objects.filter(status=DobChangeRequest.STATUS_PENDING).count()

    return {
        "unread_messages_count": unread_count,
        "pending_friend_requests_count": pending_requests,
        "pending_dob_requests_count": pending_dob,
    }


