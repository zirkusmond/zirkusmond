from rest_framework.serializers import ModelSerializer, SerializerMethodField

from events.serializers import EventSerializer
from shows.models import Show


class ShowCardSerializer(ModelSerializer):
    event_dates = SerializerMethodField()

    class Meta:
        model = Show
        fields = ["id", "title", "card_image", "event_dates", "sold_out"]

    def get_event_dates(self, show):
        return [event.time_and_date() for event in show.future_events()]


class ShowDetailSerializer(ModelSerializer):
    upcoming_events = EventSerializer(read_only=True, many=True, source="future_events")

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
            "base_ticket_price",
            "min_ticket_price",
            "max_ticket_price",
            "reservation_price",
            "third_party_reservation",
            "third_party_reservation_link",
            "upcoming_events",
            "last_modified",
            "reservation_open",
            "sold_out",
        ]
