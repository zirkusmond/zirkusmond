"""
Django management command to export all newsletter subscribers to Listmonk.

Usage:
    python manage.py export_subscribers_to_listmonk

This command:
1. Fetches all email addresses from the NewsletterRegistration model
2. Bulk imports them into Listmonk via the API
"""

from django.core.management.base import BaseCommand

from newsletter.listmonk import bulk_import_subscribers
from newsletter.models import NewsletterRegistration


class Command(BaseCommand):
    help = "Export all newsletter subscribers to Listmonk"

    def handle(self, *args, **options):  # noqa: ARG002
        # Fetch all email addresses from the database
        emails = list(NewsletterRegistration.objects.values_list("email", flat=True))

        if not emails:
            self.stdout.write(self.style.WARNING("No subscribers found in database"))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(emails)} subscribers in database")
        )

        # Bulk import to Listmonk
        try:
            result = bulk_import_subscribers(emails)
            self.stdout.write(
                self.style.SUCCESS("Successfully started bulk import to Listmonk")
            )
            self.stdout.write(f"Response: {result}")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to import subscribers to Listmonk: {str(e)}")
            )
            raise
