from rest_framework.serializers import ModelSerializer

from events.models import Event


class BasicEventSerializer(ModelSerializer):
    class Meta:
        model = Event
        fields = ["time_and_date"]


class EventSerializer(ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "time_and_date",
            "admission_time",
            "reservation_capacity",
            "reservation_open",
            "sold_out",
        ]
