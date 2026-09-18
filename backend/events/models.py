from typing import ClassVar

from django.contrib import admin
from django.db import models
from django.utils import timezone

from events.utils import format_datetime
from shows.models import Show

from .managers import PastEventManager, UpcomingEventManager


class Event(models.Model):
    show = models.ForeignKey(Show, on_delete=models.SET_NULL, null=True, related_name="events")
    admission = models.DateTimeField("Admission")
    begin = models.DateTimeField("Show Begins")
    reservation_capacity = models.PositiveIntegerField(default=300)
    open_for_reservation = models.BooleanField(default=True)

    class Meta:
        ordering = ["admission"]
        verbose_name_plural = "all events"

    def __str__(self) -> str:
        show_title = self.show.title if self.show else "Unknown Show"
        return f"{show_title} on {self.date_str()}"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.begin and self.admission and self.begin < self.admission:
            raise ValidationError("Event cannot start before admission opens.")

    @admin.display(ordering="begin")
    def time_and_date(self) -> str:
        return format_datetime(self.begin, "%d.%m.%y at %H:%M")

    def date_str(self) -> str:
        return format_datetime(self.begin, "%d.%m.%y")

    def admission_time(self) -> str:
        return format_datetime(self.admission, "%H:%M")

    def show_time(self) -> str:
        return format_datetime(self.begin, "%H:%M")

    @admin.display(ordering="annotated_reservation_count")
    def reserved_tickets(self) -> str:
        if hasattr(self, "annotated_reservation_count"):
            return f"{self.annotated_reservation_count}/{self.reservation_capacity}"
        return f"{self.reservation_count()}/{self.reservation_capacity}"

    @admin.display(boolean=True, ordering="open_for_reservation")
    def reservation_open(self) -> bool:
        if not self.open_for_reservation:
            return False
        if timezone.now() > self.begin:
            return False
        return True

    def sold_out(self) -> bool:
        if self.reservation_count() > self.reservation_capacity:
            return True
        return False

    @admin.display
    def reservation_count(self) -> int:
        if hasattr(self, "annotated_reservation_count"):
            return self.annotated_reservation_count

        from django.db.models import Count

        from reservations.models import Payment

        result = Payment.objects.filter(
            reservation__event=self, status=Payment.Status.COMPLETED
        ).aggregate(
            reservations=Count("reservation", distinct=True),
            guests=Count("reservation__guests", distinct=True),
        )
        return (result["reservations"] or 0) + (result["guests"] or 0)


class UpcomingEvent(Event):
    objects: ClassVar[UpcomingEventManager] = UpcomingEventManager()

    class Meta:
        proxy = True
        verbose_name = "upcoming event"
        verbose_name_plural = (
            "  Upcoming events"  # leave spaces to have it Event up first in admin panel
        )


class PastEvent(Event):
    objects: ClassVar[PastEventManager] = PastEventManager()

    class Meta:
        proxy = True
        verbose_name = "past event"
        verbose_name_plural = "past events"
