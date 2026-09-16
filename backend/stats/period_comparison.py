from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from django.utils.safestring import mark_safe

from reservations.payments.models import Payment

from .models import PageView


def _calculate_change(current, previous):
    """Calculate percentage change from previous to current value."""
    if previous == 0:
        if current == 0:
            return 0
        return 100  # Show +100% if going from 0 to any positive value
    return round(((current - previous) / previous) * 100, 1)


def calculate_previous_period_bounds(range_spec, since):
    """Calculate the start and end times for the previous period.

    Returns (previous_since, previous_until) or (None, None) for "all time".
    """
    if since is None or range_spec.days is None:
        return None, None

    now = timezone.now()
    period_length = timedelta(days=range_spec.days)
    previous_since = now - (period_length * 2)
    previous_until = now - period_length

    return previous_since, previous_until


def get_previous_period_metrics(previous_since, previous_until):
    """Query and calculate all metrics for the previous period.

    Returns a dict with all metric values, or None if previous_since is None.
    """
    if previous_since is None:
        return None

    # PageView metrics
    prev_page_views = PageView.objects.filter(
        entered_at__gte=previous_since, entered_at__lt=previous_until
    )
    prev_human_views = prev_page_views.exclude(device_type=PageView.DeviceChoices.BOT)

    # Payment metrics
    prev_completed_payments = Payment.objects.filter(
        status=Payment.Status.COMPLETED,
        created_at__gte=previous_since,
        created_at__lt=previous_until,
    )

    prev_agg = prev_completed_payments.aggregate(
        guest_count=Count("reservation__guests"),
        reservation_count=Count("reservation", distinct=True),
    )

    prev_revenue = (
        prev_completed_payments.values("total").aggregate(revenue=Sum("total"))["revenue"] or 0
    )

    return {
        "visitors": prev_human_views.values("session_key").distinct().count(),
        "payments": prev_completed_payments.count(),
        "revenue": prev_revenue,
        "guests": prev_agg["guest_count"] + prev_agg["reservation_count"],
        "page_views": prev_human_views.count(),
        "bot_views": prev_page_views.filter(device_type=PageView.DeviceChoices.BOT).count(),
        "bounce_rate": PageView.objects.bounce_rate(since=previous_since),
    }


def format_comparison_footer(current_value, previous_value):
    """Format a comparison footer showing percentage change vs previous period.

    Returns a formatted string with colored arrow indicator or None if no comparison.
    """
    if previous_value is None:
        return None

    change = _calculate_change(current_value, previous_value)

    if change > 0:
        arrow = "↑"
        color = "#16a34a"  # green-600
    elif change < 0:
        arrow = "↓"
        color = "#dc2626"  # red-600
    else:
        arrow = "→"
        color = "#6b7280"  # gray-500

    return mark_safe(
        f'<span style="color: {color}; font-weight: 600;">{arrow} {abs(change):.1f}%</span> vs previous period'
    )
