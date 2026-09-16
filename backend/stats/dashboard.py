from django.db.models import Count, Sum

from reservations.payments.models import Payment

from .models import PageView
from .period_comparison import (
    calculate_previous_period_bounds,
    format_comparison_footer,
    get_previous_period_metrics,
)
from .ranges import range_navigation_items, range_since, resolve_range


def _format_duration(duration) -> str:
    if duration is None:
        return "–"

    total_seconds = int(duration.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}m {seconds}s"


def dashboard_callback(request, context):
    """Injects the KPI cards and range switcher shown above the charts on the admin
    index/dashboard page.

    Registered via UNFOLD["DASHBOARD_CALLBACK"] in config/settings/unfold_config.py; consumed by
    templates/admin/index.html. The charts pull their own data independently (same selected
    range, read straight off the request) via the registered components in stats/components.py.
    """
    range_spec = resolve_range(request)
    since = range_since(range_spec)

    # Calculate previous period bounds
    previous_since, previous_until = calculate_previous_period_bounds(range_spec, since)

    # Current period metrics
    page_views = PageView.objects.filter(entered_at__gte=since) if since else PageView.objects.all()
    human_views = page_views.exclude(device_type=PageView.DeviceChoices.BOT)

    completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
    if since:
        completed_payments = completed_payments.filter(created_at__gte=since)

    agg = completed_payments.aggregate(
        guest_count=Count("reservation__guests"),
        reservation_count=Count("reservation", distinct=True),
    )

    total_revenue = (
        completed_payments.values("total").aggregate(revenue=Sum("total"))["revenue"] or 0
    )
    total_guests = agg["guest_count"] + agg["reservation_count"]
    visitors = human_views.values("session_key").distinct().count()
    page_view_count = human_views.count()
    bot_views = page_views.filter(device_type=PageView.DeviceChoices.BOT).count()
    bounce_rate = PageView.objects.bounce_rate(since=since)

    # Previous period metrics
    prev_metrics = get_previous_period_metrics(previous_since, previous_until)

    context.update(
        {
            "range_options": range_navigation_items(request, active=range_spec),
            "kpis": [
                {
                    "title": "Visitors (excluding bots)",
                    "metric": visitors,
                    "footer": (
                        format_comparison_footer(visitors, prev_metrics["visitors"])
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Payments",
                    "metric": completed_payments.count(),
                    "footer": (
                        format_comparison_footer(
                            completed_payments.count(), prev_metrics["payments"]
                        )
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Revenue",
                    "metric": f"{total_revenue} €" if total_revenue else "0 €",
                    "footer": (
                        format_comparison_footer(total_revenue, prev_metrics["revenue"])
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Tickets sold",
                    "metric": total_guests,
                    "footer": (
                        format_comparison_footer(total_guests, prev_metrics["guests"])
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Page views (excluding bots)",
                    "metric": page_view_count,
                    "footer": (
                        format_comparison_footer(page_view_count, prev_metrics["page_views"])
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Bounce rate",
                    "metric": f"{bounce_rate}%",
                    "footer": (
                        format_comparison_footer(bounce_rate, prev_metrics["bounce_rate"])
                        if prev_metrics
                        else None
                    ),
                },
                {
                    "title": "Avg. time on site",
                    "metric": _format_duration(PageView.objects.avg_time_on_site(since=since)),
                },
                {
                    "title": "Bot views",
                    "metric": bot_views,
                    "footer": (
                        format_comparison_footer(bot_views, prev_metrics["bot_views"])
                        if prev_metrics
                        else None
                    ),
                },
            ],
            "visits_chart_title": "Visits (excluding bots)",
            "device_chart_title": "Sessions by device",
        }
    )
    return context
