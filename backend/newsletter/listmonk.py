import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ListmonkAPIError(Exception):
    """Raised when Listmonk API returns an error"""

    pass


def subscribe_to_listmonk(email: str) -> None:
    """
    Subscribe an email address to Listmonk.

    Args:
        email: The email address to subscribe

    Raises:
        ListmonkAPIError: If the API call fails
    """
    url = f"{settings.LISTMONK_URL}/api/subscribers"
    auth = (settings.LISTMONK_API_USERNAME, settings.LISTMONK_API_PASSWORD)

    # Listmonk API expects JSON payload with subscriber data
    # https://listmonk.app/docs/apis/subscribers/#post-apisubscribers
    payload = {
        "email": email,
        "name": "",  # Optional: we don't collect names
        "status": "enabled",  # Single opt-in
        "lists": [settings.LISTMONK_LIST_ID],  # Subscribe to default list
        "preconfirm_subscriptions": True,  # Skip double opt-in
    }

    try:
        response = requests.post(url, json=payload, auth=auth, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully subscribed {email} to Listmonk")
    except requests.exceptions.HTTPError as e:
        # Check if it's a duplicate subscriber error (usually 409)
        if response.status_code == 409:
            logger.info(f"Subscriber {email} already exists in Listmonk")
            return
        logger.error(f"Listmonk API error for {email}: {response.text}")
        raise ListmonkAPIError(f"Failed to subscribe {email}: {response.text}") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Listmonk API connection error for {email}: {str(e)}")
        raise ListmonkAPIError(f"Connection error: {str(e)}") from e


def bulk_import_subscribers(emails: list[str]) -> dict:
    """
    Bulk import subscribers to Listmonk via the import API.

    Args:
        emails: List of email addresses to import

    Returns:
        dict: Import response from Listmonk API

    Raises:
        ListmonkAPIError: If the API call fails
    """
    url = f"{settings.LISTMONK_URL}/api/import/subscribers"
    auth = (settings.LISTMONK_API_USERNAME, settings.LISTMONK_API_PASSWORD)

    # Format CSV data for bulk import
    # https://listmonk.app/docs/apis/import/#post-apiimportsubscribers
    csv_data = "email,name,status\n"
    csv_data += "\n".join([f"{email},,enabled" for email in emails])

    payload = {
        "mode": "subscribe",  # subscribe, blacklist, or delete
        "lists": [settings.LISTMONK_LIST_ID],
        "overwrite": True,  # Update existing subscribers
        "delim": ",",
    }

    files = {"file": ("subscribers.csv", csv_data, "text/csv")}

    try:
        response = requests.post(url, data=payload, files=files, auth=auth, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully started bulk import of {len(emails)} subscribers")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Listmonk bulk import error: {str(e)}")
        raise ListmonkAPIError(f"Bulk import failed: {str(e)}") from e
