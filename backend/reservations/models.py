import uuid

from django.contrib import admin
from django.db import models

from events.models import Event


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event, on_delete=models.SET_NULL, null=True, related_name="reservations"
    )
    first_name = models.CharField(max_length=25)
    last_name = models.CharField(max_length=25)
    email = models.EmailField()
    checked_in = models.BooleanField(default=False)

    @admin.display
    def ticket_count(self) -> int:
        if hasattr(self, "annotated_guest_count"):
            return self.annotated_guest_count + 1
        return self.guests.count() + 1

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Guest(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="guests")
    first_name = models.CharField(max_length=25)
    last_name = models.CharField(max_length=25)
    ticket_id = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False, null=True, blank=True
    )
    checked_in = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Guest: {self.first_name}, {self.last_name}"


from reservations.payments.models import Payment  # noqa: E402, F401
