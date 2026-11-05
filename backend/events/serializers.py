from rest_framework.serializers import ModelSerializer, SerializerMethodField

from events.models import Event


class BasicEventSerializer(ModelSerializer):
    class Meta:
        model = Event
        fields = ["time_and_date"]


class EventSerializer(ModelSerializer):
    remaining_capacity = SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "time_and_date",
            "admission_time",
            "begin",
            "admission",
            "reservation_capacity",
            "remaining_capacity",
            "reservation_open",
            "sold_out",
        ]

    def get_remaining_capacity(self, event: Event) -> int:
        return max(0, event.reservation_capacity - event.reservation_count())
