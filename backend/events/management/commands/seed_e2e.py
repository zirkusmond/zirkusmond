import json
from datetime import timedelta
from io import BytesIO
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from events.models import Event
from shows.models import Show

E2E_SHOW_TITLE = "E2E Testshow"
E2E_STAFF_USERNAME = "e2e-staff"
E2E_STAFF_PASSWORD = "e2e-pass"


def _image(name: str, size: tuple[int, int], color: str) -> ContentFile:
    buf = BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=name)


class Command(BaseCommand):
    help = "Seed the E2E database with one bookable show/event and a staff user (prints JSON)."

    def handle(self, *args: Any, **options: Any) -> None:
        if settings.SETTINGS_MODULE != "config.settings.e2e":
            raise CommandError(
                "seed_e2e must be run with DJANGO_SETTINGS_MODULE=config.settings.e2e"
            )

        show = Show.objects.create(
            title=E2E_SHOW_TITLE,
            description="<p>Eine Show für End-to-End-Tests.</p>",
            cast="<p>Das Testteam.</p>",
            base_ticket_price=15,
            card_image=_image("e2e-card.png", (400, 300), "lightblue"),
            banner_image=_image("e2e-banner.png", (400, 225), "darkblue"),
        )

        day = timezone.localtime() + timedelta(days=7)
        event = Event.objects.create(
            show=show,
            admission=day.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=day.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=50,
            open_for_reservation=True,
        )

        user_model = get_user_model()
        user_model.objects.filter(username=E2E_STAFF_USERNAME).delete()
        user_model.objects.create_user(
            E2E_STAFF_USERNAME, password=E2E_STAFF_PASSWORD, is_staff=True, is_superuser=True
        )

        self.stdout.write(
            json.dumps(
                {
                    "showId": show.id,
                    "showTitle": show.title,
                    "eventId": event.id,
                    "eventTimeAndDate": event.time_and_date(),
                    "ticketPrice": show.base_ticket_price,
                    "staffUsername": E2E_STAFF_USERNAME,
                    "staffPassword": E2E_STAFF_PASSWORD,
                }
            )
        )
