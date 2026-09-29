"""Concrete KPI implementations for the dashboard.

Add new KPIs by subclassing KPI from kpi_registry and registering them at the bottom.
"""

from datetime import datetime, timedelta

from django.db.models import Count, Sum

from newsletter.models import NewsletterSubscription
from reservations.payments.models import Payment

from .kpi_registry import KPI, registry
from .models import PageView


def _format_duration(duration: timedelta | None) -> str:
    """Format a timedelta as 'Xm Ys'."""
    if duration is None:
        return "–"
    total_seconds = int(duration.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}m {seconds}s"


class VisitorsKPI(KPI):
    title = "Visitors (excluding bots)"
    key = "visitors"

    def calculate(self, since: datetime | None):
        page_views = (
            PageView.objects.filter(entered_at__gte=since) if since else PageView.objects.all()
        )
        human_views = page_views.exclude(device_type=PageView.DeviceChoices.BOT)
        return human_views.values("session_key").distinct().count()


class PaymentsKPI(KPI):
    title = "Payments"
    key = "payments"

    def calculate(self, since: datetime | None):
        completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
        if since:
            completed_payments = completed_payments.filter(created_at__gte=since)
        return completed_payments.count()


class RevenueKPI(KPI):
    title = "Revenue"
    key = "revenue"

    def calculate(self, since: datetime | None):
        completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
        if since:
            completed_payments = completed_payments.filter(created_at__gte=since)
        total_revenue = (
            completed_payments.values("total").aggregate(revenue=Sum("total"))["revenue"] or 0
        )
        return total_revenue

    def format_metric(self, value):
        return f"{value} €" if value else "0 €"


class GuestsKPI(KPI):
    title = "Tickets sold"
    key = "guests"

    def calculate(self, since: datetime | None):
        completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
        if since:
            completed_payments = completed_payments.filter(created_at__gte=since)
        agg = completed_payments.aggregate(
            guest_count=Count("reservation__guests"),
            reservation_count=Count("reservation", distinct=True),
        )
        return agg["guest_count"] + agg["reservation_count"]


class PageViewsKPI(KPI):
    title = "Page views (excluding bots)"
    key = "page_views"

    def calculate(self, since: datetime | None):
        page_views = (
            PageView.objects.filter(entered_at__gte=since) if since else PageView.objects.all()
        )
        human_views = page_views.exclude(device_type=PageView.DeviceChoices.BOT)
        return human_views.count()


class BounceRateKPI(KPI):
    title = "Bounce rate"
    key = "bounce_rate"

    def calculate(self, since: datetime | None):
        return PageView.objects.bounce_rate(since=since)

    def format_metric(self, value):
        return f"{value}%"


class NewsletterSubscriptionsKPI(KPI):
    title = "Newsletter Subscriptions"
    key = "newsletter_subscriptions"

    def calculate(self, since: datetime | None):
        if since:
            return NewsletterSubscription.objects.filter(created_at__gte=since).count()
        return NewsletterSubscription.objects.count()


class AvgTimeOnSiteKPI(KPI):
    title = "Avg. time on site"
    key = "avg_time_on_site"
    supports_comparison = False

    def calculate(self, since: datetime | None):
        return PageView.objects.avg_time_on_site(since=since)

    def format_metric(self, value):
        return _format_duration(value)


class BotViewsKPI(KPI):
    title = "Bot views"
    key = "bot_views"

    def calculate(self, since: datetime | None):
        page_views = (
            PageView.objects.filter(entered_at__gte=since) if since else PageView.objects.all()
        )
        return page_views.filter(device_type=PageView.DeviceChoices.BOT).count()


# Register all KPIs in the desired display order
registry.register(VisitorsKPI())
registry.register(PaymentsKPI())
registry.register(RevenueKPI())
registry.register(GuestsKPI())
registry.register(PageViewsKPI())
registry.register(BounceRateKPI())
registry.register(NewsletterSubscriptionsKPI())
registry.register(AvgTimeOnSiteKPI())
registry.register(BotViewsKPI())
