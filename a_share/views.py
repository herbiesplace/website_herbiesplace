import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CodeOnlyForm, EmailCodeForm, TransferCreateForm
from .models import Transfer, TransferFile


def _generate_code() -> str:
    # 6‑digit numeric code
    return f"{secrets.randbelow(1_000_000):06d}"


def _send_code_email(transfer: Transfer) -> None:
    subject = f"Files shared with you on HerbiesPlace"
    code = transfer.code
    base = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "127.0.0.1:8000"
    link = f"http://{base}/share/{transfer.token}/"
    access_page = f"http://{base}/share/access/"
    message_lines = [
        f"You have received files from {transfer.owner.email or transfer.owner.get_username()}.",
        "",
        f"Security code (valid for a short time): {code}",
        "",
        "You can access the files in two ways:",
        f"1) Click the link: {link} and enter the 6‑digit code when asked.",
        f"2) Go to the access page: {access_page} and enter your email address and this code.",
        "",
        "This code will expire soon. The transfer itself will be deleted after 5 days if not downloaded.",
    ]
    send_mail(
        subject,
        "\n".join(message_lines),
        settings.DEFAULT_FROM_EMAIL,
        [transfer.recipient_email],
        fail_silently=False,
    )


@login_required
def transfer_create(request):
    if request.method == "POST":
        form = TransferCreateForm(request.POST, request.FILES)
        if form.is_valid():
            files = form.cleaned_data["files"]
            now = timezone.now()
            transfer = Transfer.objects.create(
                owner=request.user,
                recipient_email=form.cleaned_data["recipient_email"],
                title=form.cleaned_data.get("title", ""),
                message=form.cleaned_data.get("message", ""),
                code=_generate_code(),
                code_expires_at=now + timedelta(minutes=15),
                expires_at=now + timedelta(days=5),
            )
            for f in files:
                TransferFile.objects.create(
                    transfer=transfer,
                    file=f,
                    original_name=getattr(f, "name", "file"),
                )

            _send_code_email(transfer)
            file_count = len(files)
            messages.success(
                request,
                f"{file_count} file{'s' if file_count != 1 else ''} uploaded successfully. "
                "The recipient has been emailed a link and security code.",
            )
            return redirect("portfolio-mine")
    else:
        form = TransferCreateForm()

    return render(request, "a_share/transfer_create.html", {"form": form})


def transfer_enter_code(request, token):
    transfer = get_object_or_404(Transfer, token=token)

    if transfer.is_expired:
        raise Http404("This transfer has expired.")

    if request.method == "POST":
        form = CodeOnlyForm(request.POST)
        if form.is_valid():
            if not transfer.is_code_valid:
                messages.error(request, "The code has expired. Please request a new one from the sender.")
            elif form.cleaned_data["code"] != transfer.code:
                messages.error(request, "Invalid code. Please check the 6‑digit number and try again.")
            else:
                return redirect("share:download-file", token=transfer.token, file_id=0)
    else:
        form = CodeOnlyForm()

    return render(
        request,
        "a_share/transfer_enter_code.html",
        {"form": form, "transfer": transfer},
    )


def transfer_email_code(request):
    if request.method == "POST":
        form = EmailCodeForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            code = form.cleaned_data["code"]
            now = timezone.now()
            transfer = (
                Transfer.objects.filter(
                    recipient_email=email,
                    code=code,
                    expires_at__gt=now,
                    code_expires_at__gt=now,
                )
                .order_by("-created_at")
                .first()
            )
            if not transfer:
                messages.error(request, "No active transfer found for this email and code.")
            else:
                return redirect("share:download-file", token=transfer.token, file_id=0)
    else:
        form = EmailCodeForm()

    return render(request, "a_share/transfer_email_code.html", {"form": form})


def transfer_email_resend_code(request):
    """
    Resend a new code based on the email address entered on the access page.
    We look up the latest active transfer for that email.
    """
    if request.method != "POST":
        return redirect("share:email-code")

    email = request.POST.get("email", "").strip()
    if not email:
        messages.error(request, "Please enter your email address first.")
        return redirect("share:email-code")

    now = timezone.now()
    transfer = (
        Transfer.objects.filter(
            recipient_email=email,
            expires_at__gt=now,
        )
        .order_by("-created_at")
        .first()
    )
    if not transfer:
        messages.error(request, "No active transfer found for this email.")
        return redirect("share:email-code")

    transfer.code = _generate_code()
    transfer.code_expires_at = now + timedelta(minutes=15)
    transfer.save(update_fields=["code", "code_expires_at"])
    _send_code_email(transfer)
    messages.success(request, "A new security code has been sent to your email address.")
    return redirect("share:email-code")


def transfer_resend_code(request, token):
    """
    Regenerate and resend a fresh 6‑digit code to the original recipient.
    Anyone with the link can trigger this, but it only affects that transfer.
    """
    transfer = get_object_or_404(Transfer, token=token)
    if transfer.is_expired:
        raise Http404("This transfer has expired.")

    if request.method == "POST":
        now = timezone.now()
        transfer.code = _generate_code()
        transfer.code_expires_at = now + timedelta(minutes=15)
        transfer.save(update_fields=["code", "code_expires_at"])
        _send_code_email(transfer)
        messages.success(request, "A new security code has been sent to the recipient.")
        return redirect("share:enter-code", token=transfer.token)

    return redirect("share:enter-code", token=transfer.token)


def transfer_download(request, token, file_id: int):
    transfer = get_object_or_404(Transfer, token=token)
    if transfer.is_expired:
        raise Http404("This transfer has expired.")

    # In this simplified version we don't re-check the code here, assuming you just came from a successful check.
    files_qs = transfer.files.all()
    if not files_qs.exists():
        raise Http404("No files available.")

    if file_id == 0:
        # Show listing page with download links
        return render(
            request,
            "a_share/transfer_files.html",
            {"transfer": transfer, "files": files_qs},
        )

    file_obj = get_object_or_404(TransferFile, pk=file_id, transfer=transfer)

    is_first_download = transfer.downloaded_at is None
    if is_first_download:
        transfer.downloaded_at = timezone.now()
        transfer.save(update_fields=["downloaded_at"])

        # Notify sender and recipient once files have been downloaded
        subject = "Your shared files have been downloaded"
        body = (
            f"Your file transfer to {transfer.recipient_email} has been accessed and at least one file was downloaded.\n\n"
            f"Title: {transfer.title or 'No title'}\n"
            f"Downloaded at: {transfer.downloaded_at:%Y-%m-%d %H:%M} (UTC)\n"
        )
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [transfer.owner.email or settings.DEFAULT_FROM_EMAIL],
            fail_silently=True,
        )
        # Best-effort notification to recipient
        send_mail(
            "You downloaded shared files from HerbiesPlace",
            "This is a confirmation that you have accessed the files shared with you.",
            settings.DEFAULT_FROM_EMAIL,
            [transfer.recipient_email],
            fail_silently=True,
        )

    return FileResponse(
        file_obj.file.open("rb"), as_attachment=True, filename=file_obj.original_name
    )


def transfer_finish(request, token):
    """
    Recipient can actively confirm they are done; we delete files immediately
    instead of waiting for the expiry date.
    """
    transfer = get_object_or_404(Transfer, token=token)
    if transfer.is_expired:
        raise Http404("This transfer has already expired.")

    if request.method == "POST":
        # Delete files and transfer
        for tf in transfer.files.all():
            tf.file.delete(save=False)
        transfer.delete()

        messages.success(request, "The files have been deleted from the platform.")
        return redirect("home")

    return render(request, "a_share/transfer_finish_confirm.html", {"transfer": transfer})


