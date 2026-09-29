import logging
from typing import Any

import requests
from django.conf import settings

from newsletter.models import NewsletterSubscription

logger = logging.getLogger(__name__)


def register_newsletter_email(email: str) -> None:
    normalized_email = email.strip().lower()
    NewsletterSubscription.objects.get_or_create(email=normalized_email)

    if settings.BREVO_API_KEY:
        try:
            subscribe_to_brevo(normalized_email)
        except Exception as e:
            # Log but don't fail the request - we still have the email in Django DB
            logger.error(f"Failed to subscribe {normalized_email} to Brevo: {str(e)}")


class BrevoAPIError(Exception):
    """Raised when the Brevo API returns an error"""

    pass


def subscribe_to_brevo(email: str) -> None:
    """
    Add (or update) a contact in Brevo, attaching it to the newsletter list.

    Args:
        email: The email address to subscribe

    Raises:
        BrevoAPIError: If the API call fails
    """
    url = "https://api.brevo.com/v3/contacts"
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # https://developers.brevo.com/reference/createcontact
    payload: dict[str, Any] = {"email": email, "updateEnabled": True}
    if settings.BREVO_NEWSLETTER_LIST_ID:
        payload["listIds"] = [int(settings.BREVO_NEWSLETTER_LIST_ID)]

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully subscribed {email} to Brevo")
    except requests.exceptions.RequestException as e:
        logger.error(f"Brevo API error for {email}: {str(e)}")
        raise BrevoAPIError(f"Failed to subscribe {email}: {str(e)}") from e
