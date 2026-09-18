from datetime import timedelta
from typing import TYPE_CHECKING, ClassVar

from django.contrib import admin
from django.db import models
from django.utils import timezone
from tinymce import models as tinymce_models

from .image_processor import process_show_image
from .managers import PastShowManager, UnscheduledShowManager, UpcomingShowManager

if TYPE_CHECKING:
    from events.models import Event


class Show(models.Model):
    title = models.CharField(max_length=255)
    description = tinymce_models.HTMLField()
    cast = tinymce_models.HTMLField()
    video_link = models.CharField(max_length=255, blank=True)
    card_image = models.ImageField()
    website_link = models.CharField(max_length=255, blank=True)
    banner_image = models.ImageField(blank=True)

    private = models.BooleanField(default=False)
    third_party_reservation = models.BooleanField(
        default=False,
        help_text="Check this field if the company has their own reservation system. Tickets / reservations will not be sold on zirkusmond.de",
    )
    third_party_reservation_link = models.CharField(
        max_length=255, blank=True, help_text="External link to reserve tickets"
    )
    last_modified = models.DateTimeField(auto_now=True)

    reservation_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Only set this field if you are not selling full tickets. Guests will have to pay rest at the door",
    )
    base_ticket_price = models.PositiveIntegerField(
        blank=True, null=True, help_text="The default ticket price on the sliding scale"
    )
    min_ticket_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Minimum price for sliding scale. Defaults to base_ticket_price - 10 EUR if not set",
    )
    max_ticket_price = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Maximum price for sliding scale. Defaults to base_ticket_price + 10 EUR if not set",
    )

    def future_events(self) -> list["Event"]:
        return [e for e in self.events.all() if e.begin > timezone.now()]

    def last_event(self) -> "Event | None":
        return self.events.order_by("begin").last()

    def first_event(self) -> "Event | None":
        return self.events.order_by("begin").first()

    def __str__(self) -> str:
        return self.title

    def dates_text(self) -> str:
        # TODO
        return "/".join(map(str, self.future_events()))

    def lastmod(self) -> str:
        return self.last_modified.strftime("%Y-%m-%d")

    CARD_IMAGE_MAX_WIDTH = 900

    def save(self, *args, **kwargs):
        if self.card_image.name and not self.card_image.name.endswith(".webp"):
            content = process_show_image(
                self.card_image,
                max_width=self.CARD_IMAGE_MAX_WIDTH,
            )
            self.card_image.save(
                f"{self.card_image.name.rsplit('.', 1)[0]}.webp", content, save=False
            )
        if self.banner_image.name and not self.banner_image.name.endswith(".webp"):
            content = process_show_image(self.banner_image, max_width=1600, crop=False)
            self.banner_image.save(
                f"{self.banner_image.name.rsplit('.', 1)[0]}.webp", content, save=False
            )
        super().save(*args, **kwargs)

    @admin.display(boolean=True)
    def reservation_open(self) -> bool:
        return any(e.reservation_open() for e in self.events.all())

    @admin.display(boolean=True)
    def show_in_preview(self) -> bool:
        events = self.events.all()
        if self.private:
            return False
        if not len(events):
            return True
        last_event = max(events, key=lambda e: e.admission)
        return last_event.begin + timedelta(hours=4) > timezone.now()

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        errors: dict[str, str] = {}
        if self.reservation_price is not None and self.base_ticket_price is not None:
            errors["__all__"] = "You cannot set both reservation and ticket price, chose one."
        if self.base_ticket_price is not None:
            if self.min_ticket_price is not None and self.min_ticket_price > self.base_ticket_price:
                errors["min_ticket_price"] = "Minimum price cannot be greater than ticket price."
            if self.max_ticket_price is not None and self.max_ticket_price < self.base_ticket_price:
                errors["max_ticket_price"] = "Maximum price cannot be less than ticket price."
        if errors:
            raise ValidationError(errors)

    def get_effective_min_price(self, base_price: int | None) -> int:
        if self.min_ticket_price is not None:
            return self.min_ticket_price
        if base_price is not None:
            return max(5, base_price - 10)
        return 5

    def get_effective_max_price(self, base_price: int | None) -> int:
        if self.max_ticket_price is not None:
            return self.max_ticket_price
        if base_price is not None:
            return base_price + 10
        return 15

    def sold_out(self) -> bool:
        return all(event.sold_out() for event in self.future_events())

    class Meta:
        verbose_name_plural = "all shows"


class UpcomingShow(Show):
    objects: ClassVar[UpcomingShowManager] = UpcomingShowManager()

    class Meta:
        proxy = True
        verbose_name = "upcoming show"
        verbose_name_plural = (
            "  Upcoming shows"  # leave spaces to have it show up first in admin panel
        )


class UnscheduledShow(Show):
    objects: ClassVar[UnscheduledShowManager] = UnscheduledShowManager()

    class Meta:
        proxy = True
        verbose_name = "unscheduled show"
        verbose_name_plural = " Unscheduled shows"


class PastShow(Show):
    objects: ClassVar[PastShowManager] = PastShowManager()

    class Meta:
        proxy = True
        verbose_name = "past show"
        verbose_name_plural = "past shows"
