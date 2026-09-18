import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.functions import TruncDate
from django.test import RequestFactory, TestCase
from django.utils import timezone
from PIL import Image

from events.models import Event
from reservations.models import Guest, Payment, Reservation
from shows.models import Show

from .admin import PageViewAdmin
from .components import DeviceBreakdownBarChart, VisitorsLineChart
from .dashboard import _format_duration, dashboard_callback
from .models import PageView
from .period_comparison import _calculate_change
from .ranges import (
    RANGES_BY_KEY,
    range_bucket_labels,
    range_navigation_items,
    range_since,
    resolve_range,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def frozen_time(when: datetime):
    with patch("django.utils.timezone.now", return_value=when):
        yield


def make_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def make_show(**kwargs: Any) -> Show:
    defaults = dict(
        title="Test Show",
        description="",
        cast="",
        card_image=make_image(),
        base_ticket_price=15,
    )
    defaults.update(kwargs)
    return Show.objects.create(**defaults)


def make_event(show: Show, offset_days: int = 7) -> Event:
    base = timezone.now() + timedelta(days=offset_days)
    return Event.objects.create(
        show=show,
        admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
        begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
        reservation_capacity=150,
        open_for_reservation=True,
    )


def make_reservation(event: Event, **kwargs: Any) -> Reservation:
    defaults = dict(first_name="Test", last_name="User", email="test@example.com")
    defaults.update(kwargs)
    return Reservation.objects.create(event=event, **defaults)


def make_payment(
    reservation: Reservation,
    *,
    total: Decimal | int = 15,
    status: str = Payment.Status.COMPLETED,
    custom_ticket_price: int = 15,
    created_at: datetime | None = None,
) -> Payment:
    """Create a Payment for a reservation.

    Non-pending statuses are set via a queryset .update() so the post_save
    confirmation-email signal doesn't fire during unrelated unit tests.
    """

    def _create() -> Payment:
        payment = Payment.objects.create(
            reservation=reservation,
            total=Decimal(total),
            custom_ticket_price=custom_ticket_price,
            status=Payment.Status.PENDING,
        )
        if status != Payment.Status.PENDING:
            Payment.objects.filter(pk=payment.pk).update(status=status)
        return payment

    if created_at is not None:
        with frozen_time(created_at):
            return _create()
    return _create()


def make_page_view(
    *,
    session_key: str = "session-1",
    path: str = "/",
    device_type: str = PageView.DeviceChoices.DESKTOP,
    entered_at: datetime | None = None,
    left_at: datetime | None = None,
    user_agent: str = "",
) -> PageView:
    def _create() -> PageView:
        return PageView.objects.create(
            session_key=session_key,
            path=path,
            device_type=device_type,
            left_at=left_at,
            user_agent=user_agent,
        )

    if entered_at is not None:
        with frozen_time(entered_at):
            return _create()
    return _create()


# ---------------------------------------------------------------------------
# PageView.detect_device
# ---------------------------------------------------------------------------


class PageViewDetectDeviceTest(TestCase):
    def test_detects_bot_user_agents(self) -> None:
        for ua in ["Googlebot/2.1", "bingbot", "some crawler bot", "facebookexternalhit/1.1"]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.BOT)

    def test_detects_tablet_user_agents(self) -> None:
        for ua in ["Mozilla/5.0 (iPad; CPU OS 14_0)", "Some Tablet Browser"]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.TABLET)

    def test_detects_mobile_user_agents(self) -> None:
        for ua in [
            "Mozilla/5.0 (Linux; Android 10)",
            "Mozilla/5.0 (iPhone; CPU iPhone OS)",
            "Mobi/1.0",
        ]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.MOBILE)

    def test_defaults_to_desktop(self) -> None:
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.DESKTOP)

    def test_empty_user_agent_defaults_to_desktop(self) -> None:
        self.assertEqual(PageView.detect_device(""), PageView.DeviceChoices.DESKTOP)

    def test_detects_bots_regardless_of_case(self) -> None:
        # Real crawler UAs capitalize "Bot"; matching must not be case-sensitive.
        for ua in ["AhrefsBot", "SemrushBot", "PetalBot", "GPTBot", "ClaudeBot", "Applebot"]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.BOT)

    def test_detects_non_browser_http_clients_as_bots(self) -> None:
        for ua in [
            "python-requests/2.31.0",
            "curl/8.4.0",
            "Wget/1.21.3",
            "okhttp/4.12.0",
            "Go-http-client/1.1",
            "PostmanRuntime/7.36.0",
        ]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.BOT)

    def test_detects_ai_crawlers_as_bots(self) -> None:
        for ua in [
            "MistralAI-User/1.0",
            "Hunyuan/1.0",
            "GPTBot/1.0",
            "ChatGPT-User/1.0",
            "anthropic-ai",
            "claude-web/1.0",
            "PerplexityBot/1.0",
        ]:
            with self.subTest(ua=ua):
                self.assertEqual(PageView.detect_device(ua), PageView.DeviceChoices.BOT)


# ---------------------------------------------------------------------------
# PageViewManager
# ---------------------------------------------------------------------------


class PageViewManagerBounceRateTest(TestCase):
    def test_returns_zero_when_no_page_views(self) -> None:
        self.assertEqual(PageView.objects.bounce_rate(), 0.0)

    def test_counts_single_view_sessions_as_bounced(self) -> None:
        make_page_view(session_key="a")
        make_page_view(session_key="b", path="/one")
        make_page_view(session_key="b", path="/two")
        self.assertEqual(PageView.objects.bounce_rate(), 50.0)

    def test_filters_by_since(self) -> None:
        old = timezone.now() - timedelta(days=10)
        make_page_view(session_key="old", entered_at=old)
        make_page_view(session_key="new")
        rate = PageView.objects.bounce_rate(since=timezone.now() - timedelta(days=1))
        self.assertEqual(rate, 100.0)


class PageViewManagerAvgTimeOnSiteTest(TestCase):
    def test_returns_none_when_no_closed_page_views(self) -> None:
        make_page_view()
        self.assertIsNone(PageView.objects.avg_time_on_site())

    def test_averages_duration_of_closed_page_views(self) -> None:
        entered = timezone.now() - timedelta(minutes=5)
        make_page_view(session_key="a", entered_at=entered, left_at=entered + timedelta(seconds=60))
        make_page_view(
            session_key="b", entered_at=entered, left_at=entered + timedelta(seconds=120)
        )
        self.assertEqual(PageView.objects.avg_time_on_site(), timedelta(seconds=90))

    def test_excludes_abandoned_tabs_over_30_minutes(self) -> None:
        now = timezone.now()
        # Normal page view: 2 minutes
        make_page_view(
            session_key="a",
            entered_at=now - timedelta(minutes=62),
            left_at=now - timedelta(minutes=60),
        )
        # Abandoned tab: 8 hours (should be excluded)
        make_page_view(session_key="b", entered_at=now - timedelta(hours=8), left_at=now)

        # Average should only include the 2-minute page view
        avg = PageView.objects.avg_time_on_site()
        self.assertIsNotNone(avg)
        self.assertEqual(avg, timedelta(minutes=2))

    def test_filters_by_since(self) -> None:
        old_entered = timezone.now() - timedelta(days=10)
        make_page_view(
            session_key="old", entered_at=old_entered, left_at=old_entered + timedelta(seconds=600)
        )
        recent_entered = timezone.now() - timedelta(hours=1)
        make_page_view(
            session_key="new",
            entered_at=recent_entered,
            left_at=recent_entered + timedelta(seconds=60),
        )
        avg = PageView.objects.avg_time_on_site(since=timezone.now() - timedelta(days=1))
        self.assertEqual(avg, timedelta(seconds=60))


class PageViewManagerDeviceBreakdownTest(TestCase):
    def test_counts_by_device_type(self) -> None:
        make_page_view(session_key="a", device_type=PageView.DeviceChoices.DESKTOP)
        make_page_view(session_key="b", device_type=PageView.DeviceChoices.MOBILE)
        make_page_view(session_key="c", device_type=PageView.DeviceChoices.MOBILE)
        make_page_view(session_key="d", device_type=PageView.DeviceChoices.BOT)
        self.assertEqual(PageView.objects.device_breakdown(), {"desktop": 1, "mobile": 2, "bot": 1})

    def test_filters_by_since(self) -> None:
        old = timezone.now() - timedelta(days=10)
        make_page_view(session_key="old", entered_at=old, device_type=PageView.DeviceChoices.TABLET)
        make_page_view(session_key="new", device_type=PageView.DeviceChoices.DESKTOP)
        breakdown = PageView.objects.device_breakdown(since=timezone.now() - timedelta(days=1))
        self.assertEqual(breakdown, {"desktop": 1})


class PageViewManagerVisitsPerBucketTest(TestCase):
    def test_buckets_distinct_sessions_and_excludes_bots(self) -> None:
        day1 = datetime(2026, 1, 10, 9, 0, tzinfo=UTC)
        day2 = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)

        make_page_view(session_key="a", entered_at=day1)
        make_page_view(session_key="a", path="/two", entered_at=day1 + timedelta(hours=1))
        make_page_view(session_key="b", entered_at=day1)
        make_page_view(session_key="bot", entered_at=day1, device_type=PageView.DeviceChoices.BOT)
        make_page_view(session_key="c", entered_at=day2)

        counts = PageView.objects.visits_per_bucket(TruncDate)

        bucket1 = timezone.localtime(day1).date()
        bucket2 = timezone.localtime(day2).date()
        self.assertEqual(counts[bucket1], 2)
        self.assertEqual(counts[bucket2], 1)

    def test_filters_by_since(self) -> None:
        old = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        make_page_view(session_key="old", entered_at=old)
        make_page_view(session_key="new")

        counts = PageView.objects.visits_per_bucket(
            TruncDate, since=timezone.now() - timedelta(days=1)
        )
        self.assertNotIn(timezone.localtime(old).date(), counts)


# ---------------------------------------------------------------------------
# ranges.py
# ---------------------------------------------------------------------------


class ResolveRangeTest(TestCase):
    def test_defaults_to_day_range(self) -> None:
        request = RequestFactory().get("/mondmin/")
        self.assertEqual(resolve_range(request).key, "day")

    def test_uses_range_query_param(self) -> None:
        request = RequestFactory().get("/mondmin/", {"range": "week"})
        self.assertEqual(resolve_range(request).key, "week")

    def test_falls_back_to_default_for_unknown_key(self) -> None:
        request = RequestFactory().get("/mondmin/", {"range": "decade"})
        self.assertEqual(resolve_range(request).key, "day")


class RangeSinceTest(TestCase):
    def test_returns_none_for_all_time(self) -> None:
        self.assertIsNone(range_since(RANGES_BY_KEY["all"]))

    def test_returns_trailing_window_start(self) -> None:
        now = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        with frozen_time(now):
            since = range_since(RANGES_BY_KEY["week"])
        self.assertEqual(since, now - timedelta(days=7))


class RangeNavigationItemsTest(TestCase):
    def test_marks_active_range_and_preserves_query_params(self) -> None:
        request = RequestFactory().get("/mondmin/", {"range": "week", "foo": "bar"})
        items = range_navigation_items(request, active=RANGES_BY_KEY["week"])

        active_items = [item for item in items if item["active"]]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["title"], "Last 7 days")

        day_item = next(item for item in items if item["title"] == "Last 24 hours")
        self.assertFalse(day_item["active"])
        self.assertIn("range=day", day_item["link"])
        self.assertIn("foo=bar", day_item["link"])


class RangeBucketLabelsTest(TestCase):
    def test_hourly_buckets_for_day_range(self) -> None:
        now = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        since = now - timedelta(days=1)
        with frozen_time(now):
            buckets = range_bucket_labels(RANGES_BY_KEY["day"], since)

        expected_start = timezone.localtime(since).replace(minute=0, second=0, microsecond=0)
        expected_end = timezone.localtime(now).replace(minute=0, second=0, microsecond=0)

        self.assertEqual(buckets[0], expected_start)
        self.assertEqual(buckets[-1], expected_end)
        self.assertEqual(
            len(buckets), int((expected_end - expected_start).total_seconds() // 3600) + 1
        )

    def test_daily_buckets_for_week_range(self) -> None:
        now = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        since = now - timedelta(days=7)
        with frozen_time(now):
            buckets = range_bucket_labels(RANGES_BY_KEY["week"], since)

        expected_start = timezone.localtime(since).date()
        expected_end = timezone.localtime(now).date()

        self.assertEqual(buckets[0], expected_start)
        self.assertEqual(buckets[-1], expected_end)
        self.assertEqual(len(buckets), (expected_end - expected_start).days + 1)

    def test_monthly_buckets_for_all_time_with_no_page_views(self) -> None:
        now = datetime(2026, 1, 15, 10, 30, tzinfo=UTC)
        with frozen_time(now):
            buckets = range_bucket_labels(RANGES_BY_KEY["all"], None)

        self.assertEqual(buckets, [timezone.localtime(now).date().replace(day=1)])

    def test_monthly_buckets_for_all_time_use_earliest_page_view(self) -> None:
        now = datetime(2026, 6, 15, 10, 30, tzinfo=UTC)
        earliest = datetime(2025, 3, 1, 8, 0, tzinfo=UTC)
        make_page_view(entered_at=earliest)

        with frozen_time(now):
            buckets = range_bucket_labels(RANGES_BY_KEY["all"], None)

        expected_start = timezone.localtime(earliest).date().replace(day=1)
        expected_end = timezone.localtime(now).date().replace(day=1)
        expected_count = (
            (expected_end.year - expected_start.year) * 12
            + (expected_end.month - expected_start.month)
            + 1
        )

        self.assertEqual(buckets[0], expected_start)
        self.assertEqual(buckets[-1], expected_end)
        self.assertEqual(len(buckets), expected_count)


# ---------------------------------------------------------------------------
# dashboard.py
# ---------------------------------------------------------------------------


class FormatDurationTest(TestCase):
    def test_returns_dash_for_none(self) -> None:
        self.assertEqual(_format_duration(None), "–")

    def test_formats_minutes_and_seconds(self) -> None:
        self.assertEqual(_format_duration(timedelta(seconds=125)), "2m 5s")

    def test_formats_zero_duration(self) -> None:
        self.assertEqual(_format_duration(timedelta(seconds=0)), "0m 0s")


class CalculateChangeTest(TestCase):
    def test_calculates_positive_change(self) -> None:
        self.assertEqual(_calculate_change(150, 100), 50.0)

    def test_calculates_negative_change(self) -> None:
        self.assertEqual(_calculate_change(50, 100), -50.0)

    def test_returns_zero_when_no_change(self) -> None:
        self.assertEqual(_calculate_change(100, 100), 0.0)

    def test_returns_100_when_previous_is_zero_and_current_is_positive(self) -> None:
        self.assertEqual(_calculate_change(50, 0), 100)

    def test_returns_zero_when_both_are_zero(self) -> None:
        self.assertEqual(_calculate_change(0, 0), 0)

    def test_rounds_to_one_decimal_place(self) -> None:
        self.assertEqual(_calculate_change(103, 100), 3.0)
        self.assertEqual(_calculate_change(106, 100), 6.0)


class DashboardCallbackTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show(base_ticket_price=15)
        self.event = make_event(self.show)

    def _callback(self, params: dict | None = None) -> dict:
        request = RequestFactory().get("/mondmin/", params or {})
        return dashboard_callback(request, {})

    def _kpis(self, context: dict) -> dict:
        return {kpi["title"]: kpi["metric"] for kpi in context["kpis"]}

    def test_kpis_are_empty_with_no_data(self) -> None:
        kpis = self._kpis(self._callback())
        self.assertEqual(kpis["Visitors (excluding bots)"], 0)
        self.assertEqual(kpis["Payments"], 0)
        self.assertEqual(kpis["Revenue"], "0 €")
        self.assertEqual(kpis["Tickets sold"], 0)
        self.assertEqual(kpis["Page views (excluding bots)"], 0)
        self.assertEqual(kpis["Bounce rate"], "0.0%")
        self.assertEqual(kpis["Avg. time on site"], "–")
        self.assertEqual(kpis["Bot views"], 0)

    def test_counts_only_completed_payments_within_range(self) -> None:
        reservation = make_reservation(self.event)
        make_payment(reservation, total=Decimal("30.00"), status=Payment.Status.COMPLETED)
        pending_reservation = make_reservation(self.event, email="pending@example.com")
        make_payment(pending_reservation, total=Decimal("50.00"), status=Payment.Status.PENDING)

        kpis = self._kpis(self._callback())
        self.assertEqual(kpis["Payments"], 1)
        self.assertEqual(kpis["Revenue"], "30 €")
        self.assertEqual(kpis["Tickets sold"], 1)

    def test_tickets_sold_counts_purchaser_and_guests(self) -> None:
        reservation = make_reservation(self.event)
        Guest.objects.create(reservation=reservation, first_name="A", last_name="B")
        Guest.objects.create(reservation=reservation, first_name="C", last_name="D")
        make_payment(reservation, total=Decimal("45.00"))

        kpis = self._kpis(self._callback())
        self.assertEqual(kpis["Tickets sold"], 3)

    def test_excludes_payments_outside_range(self) -> None:
        reservation = make_reservation(self.event)
        old = timezone.now() - timedelta(days=10)
        make_payment(reservation, total=Decimal("30.00"), created_at=old)

        kpis = self._kpis(self._callback())
        self.assertEqual(kpis["Payments"], 0)
        self.assertEqual(kpis["Revenue"], "0 €")

    def test_visitors_and_page_views_exclude_bots(self) -> None:
        make_page_view(session_key="human-1")
        make_page_view(session_key="human-1", path="/two")
        make_page_view(session_key="human-2")
        make_page_view(session_key="bot-1", device_type=PageView.DeviceChoices.BOT)

        kpis = self._kpis(self._callback())
        self.assertEqual(kpis["Visitors (excluding bots)"], 2)
        self.assertEqual(kpis["Page views (excluding bots)"], 3)
        self.assertEqual(kpis["Bot views"], 1)

    def test_range_query_param_switches_window(self) -> None:
        old = timezone.now() - timedelta(days=10)
        make_page_view(session_key="old-visitor", entered_at=old)

        day_kpis = self._kpis(self._callback())
        self.assertEqual(day_kpis["Visitors (excluding bots)"], 0)

        month_context = self._callback({"range": "month"})
        month_kpis = self._kpis(month_context)
        self.assertEqual(month_kpis["Visitors (excluding bots)"], 1)
        self.assertTrue(
            any(
                item["active"]
                for item in month_context["range_options"]
                if item["title"] == "Last 30 days"
            )
        )

    def test_includes_chart_titles(self) -> None:
        context = self._callback({"range": "week"})
        self.assertEqual(context["visits_chart_title"], "Visits (excluding bots)")
        self.assertEqual(context["device_chart_title"], "Sessions by device")

    def test_includes_previous_period_comparison_in_footer(self) -> None:
        now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)

        # Current period: last 7 days (June 3-10) - 3 payments
        current_period_start = now - timedelta(days=7)
        reservation1 = make_reservation(self.event)
        make_payment(reservation1, total=Decimal("30.00"), created_at=current_period_start)
        reservation2 = make_reservation(self.event, email="test2@example.com")
        make_payment(
            reservation2,
            total=Decimal("30.00"),
            created_at=current_period_start + timedelta(days=1),
        )
        reservation3 = make_reservation(self.event, email="test3@example.com")
        make_payment(
            reservation3,
            total=Decimal("30.00"),
            created_at=current_period_start + timedelta(days=2),
        )

        # Previous period: June 27-June 3 (7 days before) - 2 payments
        previous_period_start = now - timedelta(days=14)
        reservation4 = make_reservation(self.event, email="test4@example.com")
        make_payment(reservation4, total=Decimal("30.00"), created_at=previous_period_start)
        reservation5 = make_reservation(self.event, email="test5@example.com")
        make_payment(
            reservation5,
            total=Decimal("30.00"),
            created_at=previous_period_start + timedelta(days=1),
        )

        with frozen_time(now):
            context = self._callback({"range": "week"})

        kpis_with_footer = {kpi["title"]: kpi.get("footer") for kpi in context["kpis"]}

        # 3 payments vs 2 payments = +50% change
        self.assertIsNotNone(kpis_with_footer["Payments"])
        self.assertIn("50.0%", kpis_with_footer["Payments"])
        self.assertIn("vs previous period", kpis_with_footer["Payments"])
        self.assertIn("↑", kpis_with_footer["Payments"])  # Green up arrow
        self.assertIn("#16a34a", kpis_with_footer["Payments"])  # Green color

    def test_previous_period_comparison_shows_negative_change(self) -> None:
        now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)

        # Current period: 2 visitors
        make_page_view(session_key="current-1", entered_at=now - timedelta(hours=12))
        make_page_view(session_key="current-2", entered_at=now - timedelta(hours=6))

        # Previous period: 4 visitors
        prev_start = now - timedelta(days=2)
        make_page_view(session_key="prev-1", entered_at=prev_start)
        make_page_view(session_key="prev-2", entered_at=prev_start + timedelta(hours=3))
        make_page_view(session_key="prev-3", entered_at=prev_start + timedelta(hours=6))
        make_page_view(session_key="prev-4", entered_at=prev_start + timedelta(hours=9))

        with frozen_time(now):
            context = self._callback({"range": "day"})

        kpis_with_footer = {kpi["title"]: kpi.get("footer") for kpi in context["kpis"]}

        # 2 visitors vs 4 visitors = -50% change
        self.assertIsNotNone(kpis_with_footer["Visitors (excluding bots)"])
        self.assertIn("50.0%", kpis_with_footer["Visitors (excluding bots)"])
        self.assertIn("↓", kpis_with_footer["Visitors (excluding bots)"])  # Red down arrow
        self.assertIn("#dc2626", kpis_with_footer["Visitors (excluding bots)"])  # Red color

    def test_all_time_range_has_no_footer_comparison(self) -> None:
        reservation = make_reservation(self.event)
        make_payment(reservation, total=Decimal("30.00"))
        make_page_view(session_key="visitor-1")

        context = self._callback({"range": "all"})

        kpis_with_footer = {kpi["title"]: kpi.get("footer") for kpi in context["kpis"]}

        # "All time" should have None for all footers (no previous period to compare)
        self.assertIsNone(kpis_with_footer.get("Payments"))
        self.assertIsNone(kpis_with_footer.get("Visitors (excluding bots)"))
        self.assertIsNone(kpis_with_footer.get("Revenue"))


# ---------------------------------------------------------------------------
# components.py
# ---------------------------------------------------------------------------


class VisitorsLineChartTest(TestCase):
    def test_returns_labels_and_data_aligned_to_buckets(self) -> None:
        now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
        bucket_time = now - timedelta(hours=2)

        make_page_view(session_key="a", entered_at=bucket_time)
        make_page_view(session_key="b", entered_at=bucket_time)
        make_page_view(
            session_key="bot", entered_at=bucket_time, device_type=PageView.DeviceChoices.BOT
        )

        with frozen_time(now):
            request = RequestFactory().get("/mondmin/")
            context = VisitorsLineChart(request).get_context_data()

        data = json.loads(context["data"])
        self.assertEqual(data["datasets"][0]["label"], "Visits")

        bucket_label = (
            timezone.localtime(bucket_time)
            .replace(minute=0, second=0, microsecond=0)
            .strftime("%H:%M")
        )
        index = data["labels"].index(bucket_label)
        self.assertEqual(data["datasets"][0]["data"][index], 2)

    def test_empty_buckets_default_to_zero(self) -> None:
        now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
        with frozen_time(now):
            request = RequestFactory().get("/mondmin/")
            context = VisitorsLineChart(request).get_context_data()

        data = json.loads(context["data"])
        self.assertTrue(all(count == 0 for count in data["datasets"][0]["data"]))


class DeviceBreakdownBarChartTest(TestCase):
    def test_returns_counts_per_device_choice_label(self) -> None:
        make_page_view(session_key="a", device_type=PageView.DeviceChoices.MOBILE)
        make_page_view(session_key="b", device_type=PageView.DeviceChoices.MOBILE)
        make_page_view(session_key="c", device_type=PageView.DeviceChoices.DESKTOP)

        request = RequestFactory().get("/mondmin/")
        context = DeviceBreakdownBarChart(request).get_context_data()

        data = json.loads(context["data"])
        breakdown = dict(zip(data["labels"], data["datasets"][0]["data"], strict=True))
        self.assertEqual(breakdown[PageView.DeviceChoices.MOBILE.label], 2)
        self.assertEqual(breakdown[PageView.DeviceChoices.DESKTOP.label], 1)
        self.assertEqual(breakdown[PageView.DeviceChoices.BOT.label], 0)


# ---------------------------------------------------------------------------
# admin.py -- PageViewAdmin configuration
# ---------------------------------------------------------------------------


class PageViewAdminConfigTest(TestCase):
    def setUp(self) -> None:
        self.admin = PageViewAdmin(PageView, AdminSite())

    def test_readonly_fields_include_all_model_fields(self) -> None:
        expected = [f.name for f in PageView._meta.fields]
        self.assertEqual(self.admin.readonly_fields, expected)

    def test_add_permission_is_disabled(self) -> None:
        request = RequestFactory().get("/mondmin/stats/pageview/add/")
        self.assertFalse(self.admin.has_add_permission(request))

    def test_list_display_and_search_configuration(self) -> None:
        self.assertEqual(
            self.admin.list_display,
            ("path", "device_type", "session_key", "entered_at", "left_at"),
        )
        self.assertEqual(self.admin.search_fields, ("path", "session_key"))


# ---------------------------------------------------------------------------
# admin.py -- admin pages, including the dashboard index
# ---------------------------------------------------------------------------


class PageViewAdminPagesTest(TestCase):
    def setUp(self) -> None:
        self.superuser = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.superuser)

    def test_changelist_loads(self) -> None:
        make_page_view()
        response = self.client.get("/mondmin/stats/pageview/")
        self.assertEqual(response.status_code, 200)

    def test_add_view_is_forbidden(self) -> None:
        response = self.client.get("/mondmin/stats/pageview/add/")
        self.assertEqual(response.status_code, 403)


class AdminDashboardTest(TestCase):
    def setUp(self) -> None:
        self.superuser = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.superuser)

    def test_dashboard_renders_kpis_range_switcher_and_charts(self) -> None:
        show = make_show(base_ticket_price=15)
        event = make_event(show)
        reservation = make_reservation(event)
        make_payment(reservation, total=Decimal("30.00"))
        make_page_view()

        response = self.client.get("/mondmin/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Bounce rate", content)
        self.assertIn("Visits (excluding bots)", content)
        self.assertIn("Sessions by device", content)
        self.assertIn("Last 7 days", content)  # range switcher navigation item

    def test_dashboard_requires_authentication(self) -> None:
        self.client.logout()
        response = self.client.get("/mondmin/")
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# middleware.py
# ---------------------------------------------------------------------------


class PageViewMiddlewareTest(TestCase):
    def test_creates_page_view_for_normal_request(self) -> None:
        self.client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        self.assertEqual(PageView.objects.count(), 1)
        page_view = PageView.objects.get()
        self.assertEqual(page_view.path, "/")
        self.assertEqual(page_view.device_type, PageView.DeviceChoices.DESKTOP)
        self.assertTrue(page_view.session_key)
        self.assertIsNone(page_view.left_at)

    def test_detects_device_type_from_user_agent(self) -> None:
        self.client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)")
        page_view = PageView.objects.get()
        self.assertEqual(page_view.device_type, PageView.DeviceChoices.MOBILE)

    def test_closes_out_previous_page_view_on_next_request(self) -> None:
        self.client.get("/")
        first = PageView.objects.get()
        self.assertIsNone(first.left_at)

        self.client.get("/")

        first.refresh_from_db()
        self.assertIsNotNone(first.left_at)
        self.assertEqual(PageView.objects.count(), 2)

    def test_skips_admin_paths(self) -> None:
        self.client.get("/mondmin/")
        self.assertEqual(PageView.objects.count(), 0)

    def test_skips_stripe_webhook_path(self) -> None:
        self.client.post("/payments/webhook/stripe", HTTP_USER_AGENT="Stripe/1.0")
        self.assertEqual(PageView.objects.count(), 0)

    def test_skips_preload_requests(self) -> None:
        self.client.get("/", HTTP_X_PRELOAD="1")
        self.assertEqual(PageView.objects.count(), 0)

    def test_skips_ssr_internal_requests_from_localhost(self) -> None:
        self.client.get("/", REMOTE_ADDR="127.0.0.1", HTTP_USER_AGENT="node")
        self.assertEqual(PageView.objects.count(), 0)

    def test_records_referer_header(self) -> None:
        self.client.get("/", HTTP_REFERER="https://example.com")
        page_view = PageView.objects.get()
        self.assertEqual(page_view.referer, "https://example.com")
