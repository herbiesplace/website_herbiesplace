from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from a_share.models import Transfer


class Command(BaseCommand):
    help = "Send expiry warnings and delete expired private file transfers."

    def handle(self, *args, **options):
        now = timezone.now()
        warning_cutoff = now + timedelta(days=1)

        # 1) Send one-day-before warnings for undownloaded transfers
        warn_qs = Transfer.objects.filter(
            downloaded_at__isnull=True,
            warning_sent_at__isnull=True,
            expires_at__gt=now,
            expires_at__lte=warning_cutoff,
        )
        for transfer in warn_qs:
            subject = "Your shared files will expire soon"
            body_owner = (
                "This is a reminder that your shared files will be deleted in about 1 day if they are not downloaded.\n\n"
                f"Recipient: {transfer.recipient_email}\n"
                f"Title: {transfer.title or 'No title'}\n"
                f"Expires at: {transfer.expires_at:%Y-%m-%d %H:%M} (UTC)\n"
            )
            send_mail(
                subject,
                body_owner,
                settings.DEFAULT_FROM_EMAIL,
                [transfer.owner.email or settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )

            body_recipient = (
                "Files that were shared with you on HerbiesPlace will expire in about 1 day.\n"
                "If you still need them, please download them before the link expires.\n"
            )
            send_mail(
                subject,
                body_recipient,
                settings.DEFAULT_FROM_EMAIL,
                [transfer.recipient_email],
                fail_silently=True,
            )

            transfer.warning_sent_at = now
            transfer.save(update_fields=["warning_sent_at"])

        # 2) Delete expired transfers (files and records)
        expired_qs = Transfer.objects.filter(expires_at__lte=now)
        for transfer in expired_qs:
            # Delete associated files from storage
            for tf in transfer.files.all():
                tf.file.delete(save=False)
            transfer.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {warn_qs.count()} warnings and deleted {expired_qs.count()} expired transfers."
            )
        )


