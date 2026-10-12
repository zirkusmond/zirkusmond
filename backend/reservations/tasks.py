import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from reservations import emails
from reservations.models import Payment, Reservation

logger = logging.getLogger(__name__)


@shared_task
def cleanup_abandoned_payments():
    """Mark PENDING payments older than 1 hour as ABANDONED."""
    cutoff = timezone.now() - timedelta(hours=1)
    abandoned = Payment.objects.filter(status=Payment.Status.PENDING, created_at__lt=cutoff)

    count = abandoned.count()
    if count > 0:
        logger.info("Marking %d abandoned payments older than %s", count, cutoff)
        abandoned.update(status=Payment.Status.ABANDONED)
    else:
        logger.debug("No abandoned payments to mark")

    return count


@shared_task
def send_confirmation_email(reservation_id: str):
    """Send confirmation email for a completed payment."""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        emails.send_confirmation_mail(reservation)
        logger.info("Confirmation email sent for reservation=%s", reservation_id)
    except Reservation.DoesNotExist:
        logger.error("Cannot send confirmation email: reservation %s not found", reservation_id)
    except Exception as error:
        logger.error(
            "Failed to send confirmation email for reservation=%s: %s", reservation_id, error
        )
        raise


@shared_task
def send_custom_email(name: str, email_address: str, subject: str, body: str):
    """Send an admin-composed email to a single reservant."""
    try:
        emails.send_custom_mail(name, email_address, subject, body)
    except Exception as error:
        logger.error("Failed to send custom email to %s: %s", email_address, error)
        raise


@shared_task
def send_refund_email(reservation_id: str):
    """Send refund notification email."""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        emails.send_refund_mail(reservation)
        logger.info("Refund email sent for reservation=%s", reservation_id)
    except Reservation.DoesNotExist:
        logger.error("Cannot send refund email: reservation %s not found", reservation_id)
    except Exception as error:
        logger.error("Failed to send refund email for reservation=%s: %s", reservation_id, error)
        raise
