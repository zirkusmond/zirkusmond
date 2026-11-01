import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Self

from django.conf import settings
from django.contrib import admin
from django.db import models

if TYPE_CHECKING:
    from reservations.models import Reservation


class Payment(models.Model):
    if TYPE_CHECKING:
        # Set on the instance after Stripe intent creation (CreatePaymentIntentView) to
        # pass the client secret through to PaymentIntentResponseSerializer - not a DB field.
        _client_secret: str | None

    class PaymentMethod(models.TextChoices):
        CARD = "card"
        PAYPAL = "paypal"
        APPLE = "apple"
        GOOGLE = "google"
        KLARNA = "klarna"
        LINK = "link"
        UNKNOWN = "unknown"

    class Status(models.TextChoices):
        PENDING = "pending"
        COMPLETED = "completed"
        FAILED = "failed"
        REFUNDED = "refunded"
        ABANDONED = "abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, null=True, blank=True
    )
    reservation = models.ForeignKey(
        "reservations.Reservation", null=True, on_delete=models.SET_NULL
    )
    stripe_session_id = models.CharField(max_length=200, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    custom_ticket_price = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_for_reservation(
        cls,
        reservation: "Reservation",
        custom_ticket_price: int | None,
        payment_method: str | None = None,
    ) -> Self:
        if custom_ticket_price is None:
            raise ValueError("Custom ticket price must be provided")

        from reservations.models import Reservation

        reservation = Reservation.objects.select_related("event__show").get(pk=reservation.pk)
        show = reservation.event.show if reservation.event else None

        if show is None:
            raise ValueError("Reservation has no associated show")

        base = show.base_ticket_price
        min_price = show.get_effective_min_price(base)
        max_price = show.get_effective_max_price(base)

        if not (min_price <= custom_ticket_price <= max_price):
            raise ValueError(f"Custom price must be between {min_price} and {max_price}")

        ticket_price = Decimal(str(custom_ticket_price))
        total = reservation.ticket_count() * ticket_price

        return cls.objects.create(
            reservation=reservation,
            payment_method=payment_method,
            custom_ticket_price=custom_ticket_price,
            total=total,
        )

    def get_failure_url(self) -> str:
        protocol = "https" if settings.PAYMENT_USES_SSL else "http"
        return f"{protocol}://{settings.PAYMENT_HOST}/payments/{self.pk}/failure"

    def get_success_url(self) -> str:
        protocol = "https" if settings.PAYMENT_USES_SSL else "http"
        return f"{protocol}://{settings.PAYMENT_HOST}/payments/{self.pk}/success"

    @admin.display
    def ticket_count(self) -> int:
        if self.reservation is None:
            return 0
        return self.reservation.ticket_count()

    @admin.display
    def event(self) -> str:
        if self.reservation is None:
            return "—"
        return f"{self.reservation.event}"

    @property
    def ticket_price(self) -> Decimal:
        return Decimal(self.custom_ticket_price)
