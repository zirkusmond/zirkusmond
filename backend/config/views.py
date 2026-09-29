import datetime

from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from homepage_elements.services import get_active_hero_image, get_active_homepage_elements
from shows.models import Show
from shows.serializers import ShowCardSerializer


def _upcoming_shows(limit: int | None = None) -> list[Show]:
    shows_qs = Show.objects.prefetch_related("events").all()
    upcoming_shows = [show for show in shows_qs if show.show_in_preview()]
    upcoming_shows = sorted(
        upcoming_shows,
        key=lambda x: (
            datetime.date(2020, 1, 1)
            if not x.future_events()
            else x.future_events()[0].admission.date()
        ),
    )
    if limit is not None:
        upcoming_shows = upcoming_shows[:limit]
    return upcoming_shows


@api_view(["GET"])
@ensure_csrf_cookie
def homepage(request: Request) -> Response:
    shows = _upcoming_shows(limit=6)

    return Response(
        {
            "upcoming_shows": ShowCardSerializer(shows, many=True).data,
            "additional_elements": get_active_homepage_elements(),
            "hero_image": get_active_hero_image(),
        }
    )


# dummy route for sentry
def trigger_error(request: Request):
    divide_by_zero = 1 / 0  # noqa
