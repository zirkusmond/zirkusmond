"""
Django management command to export all subscribers from Mailchimp to local database.

This is a one-time migration script to ensure we have all Mailchimp subscribers
in the Django database before migrating to Listmonk.

Usage:
    python manage.py export_mailchimp_to_db
"""

import mailchimp_marketing
from django.conf import settings
from django.core.management.base import BaseCommand
from mailchimp_marketing.api_client import ApiClientError

from newsletter.models import NewsletterRegistration


class Command(BaseCommand):
    help = "Export all subscribers from Mailchimp to Django database"

    def handle(self, *args, **options):  # noqa: ARG002
        # Initialize Mailchimp client
        client = mailchimp_marketing.Client()
        client.set_config(
            {
                "api_key": settings.MAILCHIMP_API_KEY,
                "server": settings.MAILCHIMP_SERVER_PREFIX,
            }
        )

        try:
            # Fetch all list members
            # https://mailchimp.com/developer/marketing/api/list-members/list-members-info/
            offset = 0
            count = 0
            total_imported = 0

            while True:
                response = client.lists.get_list_members_info(
                    settings.MAILCHIMP_AUDIENCE_ID,
                    count=1000,  # Max per page
                    offset=offset,
                    status="subscribed",  # Only get subscribed members
                )

                members = response.get("members", [])
                if not members:
                    break

                self.stdout.write(
                    f"Processing batch {offset}-{offset + len(members)} of {response['total_items']}..."
                )

                for member in members:
                    email = member["email_address"]
                    _, created = NewsletterRegistration.objects.get_or_create(
                        email=email.lower().strip()
                    )
                    if created:
                        total_imported += 1
                        self.stdout.write(f"  + Imported: {email}")
                    else:
                        self.stdout.write(f"  = Already exists: {email}")

                count += len(members)
                offset += 1000

                if count >= response["total_items"]:
                    break

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nCompleted! Total subscribers in Mailchimp: {response['total_items']}"
                )
            )
            self.stdout.write(self.style.SUCCESS(f"Newly imported to Django DB: {total_imported}"))
            self.stdout.write(
                self.style.SUCCESS(f"Total in Django DB: {NewsletterRegistration.objects.count()}")
            )

        except ApiClientError as e:
            self.stdout.write(self.style.ERROR(f"Mailchimp API error: {e.text}"))
            raise
