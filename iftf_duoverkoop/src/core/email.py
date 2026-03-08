"""
core/email.py – Async confirmation email sending with status tracking.

Uses a background thread so the ordering view can return immediately.
The Purchase.email_status field is updated on the DB row once the
thread resolves (success or failure).

If SEND_EMAILS is False, the status is set to NOT_SENT synchronously
(no thread is spawned) and the caller should show the code directly.
"""
import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _

from iftf_duoverkoop.src.core.models import Purchase

logger = logging.getLogger(__name__)


def _send_and_update(purchase_id: int, subject: str, message: str, recipient: str) -> None:
    """
    Worker run in a daemon thread.  Sends the mail and persists the result.
    Never raises – all exceptions are caught and logged.
    """
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient])
        Purchase.objects.filter(pk=purchase_id).update(email_status=Purchase.EMAIL_SENT)
        logger.info("Confirmation email sent for purchase %s to %s", purchase_id, recipient)
    except Exception as exc:
        Purchase.objects.filter(pk=purchase_id).update(email_status=Purchase.EMAIL_FAILED)
        logger.error(
            "Failed to send confirmation email for purchase %s to %s: %s",
            purchase_id, recipient, exc,
        )


def send_confirmation_email_async(purchase: Purchase, subject: str, message: str) -> None:
    """
    Dispatch a confirmation email in a background thread.

    The purchase status is set to PENDING immediately; the thread will
    update it to SENT or FAILED once the SMTP call resolves.
    Does nothing (and sets NOT_SENT) when SEND_EMAILS is False.
    """
    if not settings.SEND_EMAILS:
        Purchase.objects.filter(pk=purchase.pk).update(email_status=Purchase.EMAIL_NOT_SENT)
        purchase.email_status = Purchase.EMAIL_NOT_SENT
        return

    # Mark as PENDING right away so the field is never left at its default
    # in case the thread is slow.
    Purchase.objects.filter(pk=purchase.pk).update(email_status=Purchase.EMAIL_PENDING)
    purchase.email_status = Purchase.EMAIL_PENDING

    t = threading.Thread(
        target=_send_and_update,
        args=(purchase.pk, subject, message, purchase.email),
        daemon=True,
        name=f"email-purchase-{purchase.pk}",
    )
    t.start()


def build_confirmation_message(purchase: Purchase) -> tuple[str, str]:
    """Return (subject, message) for a purchase confirmation email."""
    subject = _('email.subject')
    message = _('email.message_with_code') % {
        'name': purchase.name,
        'performance1': purchase.ticket1.selection(),
        'performance2': purchase.ticket2.selection(),
        'date': purchase.date.strftime('%d/%m/%Y %H:%M'),
        'verification_code': purchase.verification_code,
    }
    return subject, message

