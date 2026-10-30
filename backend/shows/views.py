from datetime import timedelta
from decimal import Decimal

from django.core import signing
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from config.views import _upcoming_shows
from events.stats import STATS_TOKEN_SALT, with_event_stats
from shows.serializers import ShowCardSerializer, ShowDetailSerializer

from .models import Show


@api_view(["GET"])
def get_show(request: Request, show_id: int) -> Response:
    show = get_object_or_404(Show, id=show_id)

    return Response({"show": ShowDetailSerializer(show).data})


@api_view(["GET"])
def all_shows(request: Request) -> Response:
    shows = _upcoming_shows()
    return Response({"upcoming_shows": ShowCardSerializer(shows, many=True).data})


@api_view(["GET"])
def get_show_stats(request: Request, show_id: int) -> Response:
    """Secret endpoint for external show organisers to retrieve stats.
    Email must be provided in admin panel"""
    show = get_object_or_404(Show, id=show_id)
    token = request.query_params.get("token")
    if not token:
        return Response({"error": "Missing token"}, status=400)
    try:
        payload = signing.loads(token, salt=STATS_TOKEN_SALT)
        if payload.get("show_id") != show.id:
            return Response({"error": "Invalid token"}, status=403)
    except signing.BadSignature:
        return Response({"error": "Invalid token"}, status=403)

    last_event = show.last_event()
    if last_event and timezone.now() > last_event.begin + timedelta(days=7):
        return Response({"error": "Token expired"}, status=403)

    events = with_event_stats(show.events.order_by("admission"))
    event_data = [
        {
            "id": event.id,
            "time_and_date": event.date_str(),
            "reservation_capacity": event.reservation_capacity,
            "reserved_tickets": getattr(event, "annotated_reservation_count", 0),
            "revenue": getattr(event, "total_revenue", None) or 0,
        }
        for event in events
    ]

    totals = {
        "reservation_capacity": sum(event["reservation_capacity"] for event in event_data),
        "reserved_tickets": sum(event["reserved_tickets"] for event in event_data),
        "revenue": sum((event["revenue"] for event in event_data), Decimal("0")),
    }

    return Response(
        {
            "show_title": show.title,
            "events": event_data,
            "totals": totals,
        }
    )
