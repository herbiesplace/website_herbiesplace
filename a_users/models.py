from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from datetime import date

class Profile(models.Model):
    ROLE_PHOTOGRAPHER = "photographer"
    ROLE_MODEL = "model"
    ROLE_MUA = "mua"
    ROLE_VISITOR = "visitor"
    ROLE_CHOICES = [
        (ROLE_PHOTOGRAPHER, "Photographer"),
        (ROLE_MODEL, "Model"),
        (ROLE_MUA, "Makeup Artist"),
        (ROLE_VISITOR, "Visitor"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='avatars/', null=True, blank=True)
    displayname = models.CharField(max_length=20, null=True, blank=True)
    info = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True, help_text="Required for age verification")
    show_adult_content = models.BooleanField(
        default=True,
        help_text="Show adult-only content (only applies if you are 18+)"
    )
    dob_change_pending = models.BooleanField(
        default=False,
        help_text="If True, DOB change requested and adult content is blocked until resolved.",
    )
    friends = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
        related_name="friends_with",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_VISITOR,
        help_text="Staff can set: photographer, model, mua, or visitor.",
    )
    
    def __str__(self):
        return str(self.user)
    
    @property
    def name(self):
        if self.displayname:
            return self.displayname
        return self.user.username 
    
    @property
    def avatar(self):
        if self.image:
            return self.image.url
        return f'{settings.STATIC_URL}images/avatar.svg'

    @property
    def can_upload_portfolio(self) -> bool:
        return self.role in {
            self.ROLE_PHOTOGRAPHER,
            self.ROLE_MODEL,
            self.ROLE_MUA,
        }
    
    @property
    def is_adult(self) -> bool:
        """Check if user is 18 or older"""
        if not self.date_of_birth:
            return False
        today = date.today()
        age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return age >= 18
    
    @property
    def can_view_adult_content(self) -> bool:
        """Check if user can view adult content (is adult AND has preference enabled)"""
        return self.is_adult and self.show_adult_content and not self.dob_change_pending


class DobChangeRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DECLINED = "declined"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DECLINED, "Declined"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dob_change_requests")
    requested_dob = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="dob_requests_resolved"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"DOB request for {self.user.username} ({self.status})"


class AuditLog(models.Model):
    ACTION_PROFILE = "profile"
    ACTION_PHOTO = "photo"
    ACTION_CHOICES = [
        (ACTION_PROFILE, "Profile"),
        (ACTION_PHOTO, "Photo"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="audit_entries")
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_actions"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    field = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}:{self.field} by {self.actor} on {self.user}"


class FriendRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_DECLINED, "Declined"),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_requests_sent")
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_sent")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_received")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.content[:30]}"
