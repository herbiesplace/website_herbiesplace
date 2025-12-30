import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def share_upload_path(instance, filename: str) -> str:
    # Keep original filename but nest under share/YYYY/MM/DD
    today = timezone.now()
    return f"share/{today:%Y/%m/%d}/{uuid.uuid4().hex}_{filename}"


class Transfer(models.Model):
    """
    A private file transfer from a logged-in user to an external recipient.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="outgoing_transfers",
    )
    recipient_email = models.EmailField()
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    code = models.CharField(max_length=6)
    code_expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    downloaded_at = models.DateTimeField(null=True, blank=True)

    warning_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Transfer to {self.recipient_email} ({self.created_at:%Y-%m-%d})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_code_valid(self) -> bool:
        return timezone.now() < self.code_expires_at


class TransferFile(models.Model):
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to=share_upload_path)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.original_name


