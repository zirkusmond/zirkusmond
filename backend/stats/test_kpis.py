"""Tests for the KPI registry system and individual KPIs."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from newsletter.models import NewsletterRegistration
from reservations.models import Guest

from .kpi_registry import KPI, KPIRegistry
from .kpis import (
    AvgTimeOnSiteKPI,
    BotViewsKPI,
    BounceRateKPI,
    GuestsKPI,
    NewsletterSubscriptionsKPI,
    PageViewsKPI,
    PaymentsKPI,
    RevenueKPI,
    VisitorsKPI,
)
from .kpis import registry as global_registry
from .models import PageView
from .tests import (
    frozen_time,
    make_event,
    make_page_view,
    make_payment,
    make_reservation,
    make_show,
)


# ---------------------------------------------------------------------------
# KPIRegistry
# ---------------------------------------------------------------------------


class KPIRegistryTest(TestCase):
    def test_register_and_get_all(self):
        registry = KPIRegistry()

        kpi1 = VisitorsKPI()
        kpi2 = PaymentsKPI()

        registry.register(kpi1)
        registry.register(kpi2)

        kpis = registry.get_all()
        self.assertEqual(len(kpis), 2)
        self.assertEqual(kpis[0], kpi1)
        self.assertEqual(kpis[1], kpi2)

    def test_kpis_are_returned_in_registration_order(self):
        registry = KPIRegistry()

        revenue = RevenueKPI()
        visitors = VisitorsKPI()
        payments = PaymentsKPI()

        registry.register(revenue)
        registry.register(visitors)
        registry.register(payments)

        kpis = registry.get_all()
        self.assertEqual(kpis[0].title, "Revenue")
        self.assertEqual(kpis[1].title, "Visitors (excluding bots)")
        self.assertEqual(kpis[2].title, "Payments")


# ---------------------------------------------------------------------------
# KPI Base Class
# ---------------------------------------------------------------------------


class DummyKPI(KPI):
    title = "Test Metric"
    key = "test_metric"

    def calculate(self, since):
        return 42


class DummyKPIWithFormatting(KPI):
    title = "Formatted Metric"
    key = "formatted_metric"

    def calculate(self, since):
        return 100

    def format_metric(self, value):
        return f"{value}%"


class DummyKPINoComparison(KPI):
    title = "No Comparison"
    key = "no_comparison"
    supports_comparison = False

    def calculate(self, since):
        return 50


class KPIBaseTest(TestCase):
    def test_render_returns_title_and_metric(self):
        kpi = DummyKPI()
        result = kpi.render(since=None, previous_metrics=None)

        self.assertEqual(result["title"], "Test Metric")
        self.assertEqual(result["metric"], 42)
        self.assertIsNone(result["footer"])

    def test_render_applies_custom_formatting(self):
        kpi = DummyKPIWithFormatting()
        result = kpi.render(since=None, previous_metrics=None)

        self.assertEqual(result["metric"], "100%")

    def test_render_includes_comparison_footer_when_previous_metrics_provided(self):
        kpi = DummyKPI()
        prev_metrics = {"test_metric": 30}

        result = kpi.render(since=None, previous_metrics=prev_metrics)

        self.assertIsNotNone(result["footer"])
        self.assertIn("40.0%", result["footer"])  # (42-30)/30 = 40%
        self.assertIn("vs previous period", result["footer"])

    def test_render_skips_footer_when_no_previous_value(self):
        kpi = DummyKPI()
        prev_metrics = {"other_metric": 100}

        result = kpi.render(since=None, previous_metrics=prev_metrics)

        self.assertIsNone(result["footer"])

    def test_render_respects_supports_comparison_false(self):
        kpi = DummyKPINoComparison()
        prev_metrics = {"no_comparison": 25}

        result = kpi.render(since=None, previous_metrics=prev_metrics)

        self.assertIsNone(result["footer"])


# ---------------------------------------------------------------------------
# Individual KPI Tests
# ---------------------------------------------------------------------------


class VisitorsKPITest(TestCase):
    def test_counts_distinct_human_visitors(self):
        make_page_view(session_key="visitor-1")
        make_page_view(session_key="visitor-1", path="/about")
        make_page_view(session_key="visitor-2")
        make_page_view(session_key="bot-1", device_type=PageView.DeviceChoices.BOT)

        kpi = VisitorsKPI()
        self.assertEqual(kpi.calculate(since=None), 2)

    def test_filters_by_since(self):
        now = timezone.now()
        old = now - timedelta(days=10)

        make_page_view(session_key="old", entered_at=old)
        make_page_view(session_key="new", entered_at=now - timedelta(hours=1))

        kpi = VisitorsKPI()
        self.assertEqual(kpi.calculate(since=now - timedelta(days=1)), 1)


class PaymentsKPITest(TestCase):
    def setUp(self):
        self.show = make_show()
        self.event = make_event(self.show)

    def test_counts_completed_payments(self):
        res1 = make_reservation(self.event)
        make_payment(res1, status="completed")
        res2 = make_reservation(self.event, email="test2@example.com")
        make_payment(res2, status="completed")
        res3 = make_reservation(self.event, email="test3@example.com")
        make_payment(res3, status="pending")

        kpi = PaymentsKPI()
        self.assertEqual(kpi.calculate(since=None), 2)

    def test_filters_by_since(self):
        now = timezone.now()
        old = now - timedelta(days=10)

        res1 = make_reservation(self.event)
        make_payment(res1, status="completed", created_at=old)
        res2 = make_reservation(self.event, email="test2@example.com")
        make_payment(res2, status="completed", created_at=now - timedelta(hours=1))

        kpi = PaymentsKPI()
        self.assertEqual(kpi.calculate(since=now - timedelta(days=1)), 1)


class RevenueKPITest(TestCase):
    def setUp(self):
        self.show = make_show()
        self.event = make_event(self.show)

    def test_sums_total_from_completed_payments(self):
        res1 = make_reservation(self.event)
        make_payment(res1, total=Decimal("30.00"), status="completed")
        res2 = make_reservation(self.event, email="test2@example.com")
        make_payment(res2, total=Decimal("45.50"), status="completed")

        kpi = RevenueKPI()
        self.assertEqual(kpi.calculate(since=None), Decimal("75.50"))

    def test_formats_with_euro_symbol(self):
        kpi = RevenueKPI()
        self.assertEqual(kpi.format_metric(Decimal("100")), "100 €")
        self.assertEqual(kpi.format_metric(0), "0 €")


class GuestsKPITest(TestCase):
    def setUp(self):
        self.show = make_show()
        self.event = make_event(self.show)

    def test_counts_guests_plus_purchasers(self):
        res1 = make_reservation(self.event)
        Guest.objects.create(reservation=res1, first_name="A", last_name="B")
        Guest.objects.create(reservation=res1, first_name="C", last_name="D")
        make_payment(res1, status="completed")

        res2 = make_reservation(self.event, email="test2@example.com")
        make_payment(res2, status="completed")

        kpi = GuestsKPI()
        # res1: 1 purchaser + 2 guests = 3
        # res2: 1 purchaser = 1
        # Total: 4
        self.assertEqual(kpi.calculate(since=None), 4)


class PageViewsKPITest(TestCase):
    def test_counts_human_page_views(self):
        make_page_view(session_key="human-1")
        make_page_view(session_key="human-1", path="/about")
        make_page_view(session_key="bot-1", device_type=PageView.DeviceChoices.BOT)

        kpi = PageViewsKPI()
        self.assertEqual(kpi.calculate(since=None), 2)


class BounceRateKPITest(TestCase):
    def test_calculates_bounce_rate(self):
        make_page_view(session_key="bounced")
        make_page_view(session_key="engaged", path="/one")
        make_page_view(session_key="engaged", path="/two")

        kpi = BounceRateKPI()
        self.assertEqual(kpi.calculate(since=None), 50.0)

    def test_formats_with_percent(self):
        kpi = BounceRateKPI()
        self.assertEqual(kpi.format_metric(75.5), "75.5%")


class NewsletterSubscriptionsKPITest(TestCase):
    def test_counts_newsletter_subscriptions(self):
        NewsletterRegistration.objects.create(email="test1@example.com")
        NewsletterRegistration.objects.create(email="test2@example.com")

        kpi = NewsletterSubscriptionsKPI()
        self.assertEqual(kpi.calculate(since=None), 2)

    def test_filters_by_since(self):
        now = timezone.now()
        old = now - timedelta(days=10)

        with frozen_time(old):
            NewsletterRegistration.objects.create(email="old@example.com")

        NewsletterRegistration.objects.create(email="new@example.com")

        kpi = NewsletterSubscriptionsKPI()
        self.assertEqual(kpi.calculate(since=now - timedelta(days=1)), 1)


class AvgTimeOnSiteKPITest(TestCase):
    def test_calculates_average_time(self):
        now = timezone.now()
        make_page_view(
            session_key="a",
            entered_at=now - timedelta(minutes=5),
            left_at=now - timedelta(minutes=4),
        )
        make_page_view(
            session_key="b",
            entered_at=now - timedelta(minutes=5),
            left_at=now - timedelta(minutes=3),
        )

        kpi = AvgTimeOnSiteKPI()
        self.assertEqual(kpi.calculate(since=None), timedelta(seconds=90))

    def test_formats_as_duration(self):
        kpi = AvgTimeOnSiteKPI()
        self.assertEqual(kpi.format_metric(timedelta(minutes=2, seconds=5)), "2m 5s")
        self.assertEqual(kpi.format_metric(None), "–")

    def test_does_not_support_comparison(self):
        kpi = AvgTimeOnSiteKPI()
        self.assertFalse(kpi.supports_comparison)


class BotViewsKPITest(TestCase):
    def test_counts_bot_page_views(self):
        make_page_view(session_key="human")
        make_page_view(session_key="bot-1", device_type=PageView.DeviceChoices.BOT)
        make_page_view(session_key="bot-2", device_type=PageView.DeviceChoices.BOT)

        kpi = BotViewsKPI()
        self.assertEqual(kpi.calculate(since=None), 2)


# ---------------------------------------------------------------------------
# Global Registry
# ---------------------------------------------------------------------------


class GlobalRegistryTest(TestCase):
    def test_all_kpis_are_registered(self):
        kpis = global_registry.get_all()

        # Should have all 9 KPIs registered
        self.assertEqual(len(kpis), 9)

        titles = [kpi.title for kpi in kpis]
        self.assertIn("Visitors (excluding bots)", titles)
        self.assertIn("Payments", titles)
        self.assertIn("Revenue", titles)
        self.assertIn("Tickets sold", titles)
        self.assertIn("Page views (excluding bots)", titles)
        self.assertIn("Bounce rate", titles)
        self.assertIn("Newsletter Subscriptions", titles)
        self.assertIn("Avg. time on site", titles)
        self.assertIn("Bot views", titles)

    def test_kpis_registered_in_correct_order(self):
        kpis = global_registry.get_all()
        titles = [kpi.title for kpi in kpis]

        # Verify the order matches what's in kpis.py
        expected_order = [
            "Visitors (excluding bots)",
            "Payments",
            "Revenue",
            "Tickets sold",
            "Page views (excluding bots)",
            "Bounce rate",
            "Newsletter Subscriptions",
            "Avg. time on site",
            "Bot views",
        ]

        self.assertEqual(titles, expected_order)

    def test_all_kpis_have_required_attributes(self):
        kpis = global_registry.get_all()

        for kpi in kpis:
            with self.subTest(kpi=kpi.title):
                self.assertTrue(hasattr(kpi, "title"))
                self.assertTrue(hasattr(kpi, "key"))
                self.assertTrue(hasattr(kpi, "calculate"))
                self.assertTrue(hasattr(kpi, "supports_comparison"))


# ---------------------------------------------------------------------------
# Integration Test: KPI with Dashboard
# ---------------------------------------------------------------------------


class KPIDashboardIntegrationTest(TestCase):
    def setUp(self):
        self.show = make_show()
        self.event = make_event(self.show)

    def test_kpis_render_correctly_for_dashboard(self):
        # Create some data
        make_page_view(session_key="visitor-1")
        make_page_view(session_key="visitor-2")

        res = make_reservation(self.event)
        make_payment(res, total=Decimal("30.00"), status="completed")

        # Render all KPIs
        now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
        with frozen_time(now):
            kpis = [
                kpi.render(since=None, previous_metrics=None) for kpi in global_registry.get_all()
            ]

        # Extract by title
        kpi_dict = {kpi["title"]: kpi for kpi in kpis}

        self.assertEqual(kpi_dict["Visitors (excluding bots)"]["metric"], 2)
        self.assertEqual(kpi_dict["Payments"]["metric"], 1)
        self.assertEqual(kpi_dict["Revenue"]["metric"], "30 €")

    def test_kpis_include_comparison_footer_with_previous_metrics(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)

        # Current period: 3 payments
        with frozen_time(now - timedelta(days=3)):
            for i in range(3):
                res = make_reservation(self.event, email=f"test{i}@example.com")
                make_payment(res, status="completed")

        prev_metrics = {
            "visitors": 5,
            "payments": 2,  # 3 current vs 2 previous = +50%
            "revenue": Decimal("40.00"),
            "guests": 3,
            "page_views": 10,
            "bounce_rate": 50.0,
            "newsletter_subscriptions": 1,
            "bot_views": 2,
        }

        with frozen_time(now):
            kpis = [
                kpi.render(since=None, previous_metrics=prev_metrics)
                for kpi in global_registry.get_all()
            ]

        payments_kpi = next(kpi for kpi in kpis if kpi["title"] == "Payments")

        self.assertIsNotNone(payments_kpi["footer"])
        self.assertIn("50.0%", payments_kpi["footer"])
        self.assertIn("vs previous period", payments_kpi["footer"])
