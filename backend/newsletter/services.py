import logging

from django.conf import settings

from newsletter.listmonk import subscribe_to_listmonk
from newsletter.models import NewsletterRegistration

logger = logging.getLogger(__name__)


def register_newsletter_email(email: str) -> None:
    normalized_email = email.strip().lower()
    NewsletterRegistration.objects.get_or_create(email=normalized_email)

    # Subscribe to Listmonk if configured
    if settings.LISTMONK_URL:
        try:
            subscribe_to_listmonk(normalized_email)
        except Exception as e:
            # Log but don't fail the request - we still have the email in Django DB
            logger.error(f"Failed to subscribe {normalized_email} to Listmonk: {str(e)}")
