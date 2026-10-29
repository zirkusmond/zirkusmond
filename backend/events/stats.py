from django.db.models import (
    Count,
    DecimalField,
    IntegerField,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from events.models import Event
from reservations.models import Guest, Payment

STATS_TOKEN_SALT = "show-stats"


def with_event_stats(queryset: QuerySet[Event]) -> QuerySet[Event]:
    """Annotate events with confirmed ticket counts and revenue."""
    confirmed_reservations = (
        Payment.objects.filter(
            reservation__event=OuterRef("pk"),
            status=Payment.Status.COMPLETED,
        )
        .values("reservation__event")
        .annotate(count=Count("reservation", distinct=True))
        .values("count")
    )

    confirmed_guests = (
        Guest.objects.filter(
            reservation__event=OuterRef("pk"),
            reservation__payment__status=Payment.Status.COMPLETED,
        )
        .values("reservation__event")
        .annotate(count=Count("pk", distinct=True))
        .values("count")
    )

    revenue_subquery = (
        Payment.objects.filter(
            reservation__event=OuterRef("pk"),
            status=Payment.Status.COMPLETED,
        )
        .values("reservation__event")
        .annotate(total=Sum("total"))
        .values("total")
    )

    return queryset.annotate(
        annotated_reservation_count=Coalesce(
            Subquery(confirmed_reservations, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
        + Coalesce(
            Subquery(confirmed_guests, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        ),
        total_revenue=Subquery(revenue_subquery, output_field=DecimalField()),
    )
