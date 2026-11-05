from rest_framework.serializers import ModelSerializer, SerializerMethodField

from events.serializers import EventSerializer
from shows.models import Show


class ShowCardSerializer(ModelSerializer):
    event_dates = SerializerMethodField()
    event_dates_iso = SerializerMethodField()

    class Meta:
        model = Show
        fields = ["id", "title", "card_image", "event_dates", "event_dates_iso", "sold_out"]

    def get_event_dates(self, show):
        return [event.time_and_date() for event in show.future_events()]

    def get_event_dates_iso(self, show):
        return [event.begin.isoformat() for event in show.future_events()]


class ShowDetailSerializer(ModelSerializer):
    upcoming_events = EventSerializer(read_only=True, many=True, source="future_events")
    currency = SerializerMethodField()
    effective_min_price = SerializerMethodField()
    effective_max_price = SerializerMethodField()

    class Meta:
        model = Show
        fields = [
            "id",
            "title",
            "description",
            "cast",
            "card_image",
            "banner_image",
            "video_link",
            "website_link",
            "currency",
            "base_ticket_price",
            "min_ticket_price",
            "max_ticket_price",
            "effective_min_price",
            "effective_max_price",
            "reservation_price",
            "third_party_reservation",
            "third_party_reservation_link",
            "upcoming_events",
            "last_modified",
            "reservation_open",
            "sold_out",
        ]

    def get_currency(self, show) -> str:
        return "EUR"

    def get_effective_min_price(self, show) -> int | None:
        if show.reservation_price is not None:
            return show.reservation_price
        if show.base_ticket_price is not None:
            return show.get_effective_min_price(show.base_ticket_price)
        return None

    def get_effective_max_price(self, show) -> int | None:
        if show.reservation_price is not None:
            return show.reservation_price
        if show.base_ticket_price is not None:
            return show.get_effective_max_price(show.base_ticket_price)
        return None
