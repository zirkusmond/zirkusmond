from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone
from PIL import Image

from events.forms import ReservationForm
from events.models import Event
from reservations.models import Guest, Payment, Reservation
from shows.models import Show

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def make_banner_image() -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (400, 225), color="blue").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile("banner.jpg", buf.read(), content_type="image/jpeg")


def make_show(**kwargs: Any) -> Show:
    defaults = dict(
        title="Test Show",
        description="",
        cast="",
        card_image=make_image(),
        banner_image=make_banner_image(),
        private=False,
        base_ticket_price=15,
    )
    defaults.update(kwargs)
    return Show.objects.create(**defaults)


def make_event(
    show: Show,
    offset_days: int = 7,
    capacity: int = 150,
    open_for_reservation: bool = True,
) -> Event:
    base = timezone.now() + timedelta(days=offset_days)
    return Event.objects.create(
        show=show,
        admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
        begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
        reservation_capacity=capacity,
        open_for_reservation=open_for_reservation,
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
) -> Payment:
    """Create a Payment for a reservation.

    Non-pending statuses are set via a queryset .update() so the post_save
    confirmation-email signal doesn't fire during unrelated unit tests.
    """
    payment = Payment.objects.create(
        reservation=reservation,
        total=Decimal(total),
        custom_ticket_price=custom_ticket_price,
        status=Payment.Status.PENDING,
    )
    if status != Payment.Status.PENDING:
        Payment.objects.filter(pk=payment.pk).update(status=status)
        payment.status = status
    return payment


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class EventModelTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)

    def test_str_contains_date(self) -> None:
        self.assertIn(".", str(self.event))

    def test_time_and_date(self) -> None:
        self.assertRegex(self.event.time_and_date(), r"\d{2}\.\d{2}\.\d{2} at \d{2}:\d{2}")

    def test_date_str(self) -> None:
        self.assertRegex(self.event.date_str(), r"\d{2}\.\d{2}\.\d{2}")

    def test_admission_time(self) -> None:
        self.assertRegex(self.event.admission_time(), r"\d{2}:\d{2}")

    def test_show_time(self) -> None:
        self.assertRegex(self.event.show_time(), r"\d{2}:\d{2}")

    def test_reservation_open_for_future_event(self) -> None:
        self.assertTrue(self.event.reservation_open())

    def test_reservation_closed_for_past_event(self) -> None:
        past = make_event(self.show, offset_days=-1)
        self.assertFalse(past.reservation_open())

    def test_reservation_closed_when_manually_closed(self) -> None:
        closed = make_event(self.show, open_for_reservation=False)
        self.assertFalse(closed.reservation_open())

    def test_reservation_open_when_over_capacity(self) -> None:
        event = make_event(self.show, capacity=1)
        make_payment(make_reservation(event))
        make_payment(make_reservation(event, email="other@example.com"))
        # reservation_open checks if event is open, not if sold out
        self.assertTrue(event.reservation_open())
        self.assertTrue(event.sold_out())

    def test_sold_out_false_when_under_capacity(self) -> None:
        event = make_event(self.show, capacity=10)
        make_payment(make_reservation(event))
        self.assertFalse(event.sold_out())

    def test_sold_out_false_at_capacity(self) -> None:
        event = make_event(self.show, capacity=1)
        make_payment(make_reservation(event))
        self.assertFalse(event.sold_out())

    def test_sold_out_true_when_over_capacity(self) -> None:
        event = make_event(self.show, capacity=1)
        make_payment(make_reservation(event))
        make_payment(make_reservation(event, email="other@example.com"))
        self.assertTrue(event.sold_out())

    def test_sold_out_false_when_no_reservations(self) -> None:
        event = make_event(self.show, capacity=10)
        self.assertFalse(event.sold_out())

    def test_reservation_count_empty(self) -> None:
        self.assertEqual(self.event.reservation_count(), 0)

    def test_reservation_count_with_payment(self) -> None:
        reservation = make_reservation(self.event)
        make_payment(reservation)
        self.assertEqual(self.event.reservation_count(), 1)

    def test_reservation_count_unconfirmed_not_counted(self) -> None:
        reservation = make_reservation(self.event)
        make_payment(reservation, status=Payment.Status.PENDING)
        self.assertEqual(self.event.reservation_count(), 0)

    def test_reservation_count_includes_guests(self) -> None:
        from reservations.models import Guest

        reservation = make_reservation(self.event)
        make_payment(reservation)
        Guest.objects.create(reservation=reservation, first_name="G", last_name="H")
        self.assertEqual(self.event.reservation_count(), 2)

    def test_reserved_tickets_display_format(self) -> None:
        reservation = make_reservation(self.event)
        make_payment(reservation)
        self.assertEqual(self.event.reserved_tickets(), "1/150")

    def test_clean_raises_if_begin_before_admission(self) -> None:
        base = timezone.now() + timedelta(days=3)
        event = Event(
            show=self.show,
            admission=base + timedelta(hours=1),
            begin=base,
            reservation_capacity=100,
        )
        with self.assertRaises(ValidationError):
            event.clean()


# ---------------------------------------------------------------------------
# Show price validation
# ---------------------------------------------------------------------------


class ShowPriceValidationTest(TestCase):
    def setUp(self) -> None:
        self.show_data = dict(
            title="Test Show",
            description="A description",
            cast="A cast",
            card_image=make_image(),
            private=False,
        )

    def test_valid_price_config_passes(self) -> None:
        show = Show(
            **self.show_data, base_ticket_price=20, min_ticket_price=10, max_ticket_price=30
        )
        show.full_clean()

    def test_negative_ticket_price_raises(self) -> None:
        show = Show(**self.show_data, base_ticket_price=-10)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("base_ticket_price", ctx.exception.message_dict)

    def test_negative_min_ticket_price_raises(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, min_ticket_price=-5)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("min_ticket_price", ctx.exception.message_dict)

    def test_negative_max_ticket_price_raises(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, max_ticket_price=-5)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("max_ticket_price", ctx.exception.message_dict)

    def test_negative_reservation_price_raises(self) -> None:
        show = Show(**self.show_data, reservation_price=-5)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("reservation_price", ctx.exception.message_dict)

    def test_min_above_ticket_price_raises(self) -> None:
        show = Show(**self.show_data, base_ticket_price=15, min_ticket_price=20)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("min_ticket_price", ctx.exception.message_dict)

    def test_max_below_ticket_price_raises(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, max_ticket_price=15)
        with self.assertRaises(ValidationError) as ctx:
            show.full_clean()
        self.assertIn("max_ticket_price", ctx.exception.message_dict)

    def test_min_equals_ticket_price_is_valid(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, min_ticket_price=20)
        show.full_clean()

    def test_max_equals_ticket_price_is_valid(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, max_ticket_price=20)
        show.full_clean()

    def test_effective_min_price_uses_custom_value(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, min_ticket_price=12)
        self.assertEqual(show.get_effective_min_price(20), 12)

    def test_effective_min_price_defaults_to_base_minus_10(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20)
        self.assertEqual(show.get_effective_min_price(20), 10)

    def test_effective_min_price_floors_at_5(self) -> None:
        show = Show(**self.show_data, base_ticket_price=8)
        self.assertEqual(show.get_effective_min_price(8), 5)

    def test_effective_max_price_uses_custom_value(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20, max_ticket_price=35)
        self.assertEqual(show.get_effective_max_price(20), 35)

    def test_effective_max_price_defaults_to_base_plus_10(self) -> None:
        show = Show(**self.show_data, base_ticket_price=20)
        self.assertEqual(show.get_effective_max_price(20), 30)


# ---------------------------------------------------------------------------
# Reservation form
# ---------------------------------------------------------------------------


class ReservationFormTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.future = timezone.now() + timedelta(days=7)
        self.past = timezone.now() - timedelta(days=1)

    def _make_event(
        self, begin: datetime, open_for_reservation: bool = True, capacity: int = 150
    ) -> Event:
        return Event.objects.create(
            show=self.show,
            admission=begin - timedelta(hours=1),
            begin=begin,
            reservation_capacity=capacity,
            open_for_reservation=open_for_reservation,
        )

    def test_future_open_event_included(self) -> None:
        event = self._make_event(self.future)
        form = ReservationForm(self.show)
        self.assertIn(event, form.fields["event"].queryset)

    def test_past_event_excluded(self) -> None:
        event = self._make_event(self.past)
        form = ReservationForm(self.show)
        self.assertNotIn(event, form.fields["event"].queryset)

    def test_manually_closed_event_excluded(self) -> None:
        event = self._make_event(self.future, open_for_reservation=False)
        form = ReservationForm(self.show)
        self.assertNotIn(event, form.fields["event"].queryset)

    def test_sold_out_event_included(self) -> None:
        event = self._make_event(self.future, capacity=1)
        for r in [make_reservation(event), make_reservation(event, email="other@example.com")]:
            make_payment(r)
        form = ReservationForm(self.show)
        # Sold out events are still included (frontend filters them)
        self.assertIn(event, form.fields["event"].queryset)

    def test_open_and_closed_events_filtered_correctly(self) -> None:
        open_event = self._make_event(self.future)
        past_event = self._make_event(self.past)
        closed_event = self._make_event(self.future, open_for_reservation=False)
        qs = ReservationForm(self.show).fields["event"].queryset
        self.assertIn(open_event, qs)
        self.assertNotIn(past_event, qs)
        self.assertNotIn(closed_event, qs)

    def test_valid_form_with_all_fields(self) -> None:
        event = self._make_event(self.future)
        form = ReservationForm(
            self.show,
            data={
                "event": event.pk,
                "attendee_count": 2,
                "first_name": "Anna",
                "last_name": "Smith",
                "email": "anna@example.com",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields_invalid(self) -> None:
        form = ReservationForm(self.show, data={})
        self.assertFalse(form.is_valid())


# ---------------------------------------------------------------------------
# EventAdmin revenue annotation and display
# ---------------------------------------------------------------------------


class EventAdminRevenueTest(TestCase):
    def setUp(self) -> None:
        from events.admin import EventAdmin

        self.show = make_show(base_ticket_price=15)
        self.event = make_event(self.show)
        self.user = User.objects.create_superuser("admin", "admin@example.com", "password")
        self.site = AdminSite()
        self.admin = EventAdmin(Event, self.site)
        self.factory = RequestFactory()

    def _get_annotated_event(self) -> Event:
        request = self.factory.get("/")
        request.user = self.user
        return self.admin.get_queryset(request).get(pk=self.event.pk)

    def _make_payment(
        self,
        reservation: Reservation,
        total: Decimal,
        status: str = Payment.Status.COMPLETED,
    ) -> Payment:
        return make_payment(reservation, total=total, status=status)

    def test_revenue_display_returns_dash_when_no_payments(self) -> None:
        event = self._get_annotated_event()
        self.assertIsNone(event.total_revenue)
        self.assertEqual(self.admin.revenue(event), "—")

    def test_revenue_display_returns_formatted_euro_amount(self) -> None:
        reservation = make_reservation(self.event)
        self._make_payment(reservation, Decimal("30.00"))
        event = self._get_annotated_event()
        self.assertEqual(self.admin.revenue(event), "€ 30.00")

    def test_total_revenue_sums_multiple_confirmed_payments(self) -> None:
        for i, amount in enumerate([Decimal("15.00"), Decimal("30.00"), Decimal("45.00")]):
            reservation = make_reservation(self.event, email=f"p{i}@example.com")
            self._make_payment(reservation, amount)
        event = self._get_annotated_event()
        self.assertEqual(event.total_revenue, Decimal("90.00"))
        self.assertEqual(self.admin.revenue(event), "€ 90.00")

    def test_total_revenue_excludes_non_confirmed_payments(self) -> None:
        reservation = make_reservation(self.event)
        self._make_payment(reservation, Decimal("50.00"), status=Payment.Status.PENDING)
        event = self._get_annotated_event()
        self.assertIsNone(event.total_revenue)
        self.assertEqual(self.admin.revenue(event), "—")

    def test_total_revenue_only_counts_confirmed_among_mixed_statuses(self) -> None:
        reservation = make_reservation(self.event)
        self._make_payment(reservation, Decimal("20.00"), status=Payment.Status.COMPLETED)
        reservation2 = make_reservation(self.event, email="b@example.com")
        self._make_payment(reservation2, Decimal("100.00"), status=Payment.Status.PENDING)
        event = self._get_annotated_event()
        self.assertEqual(event.total_revenue, Decimal("20.00"))


# ---------------------------------------------------------------------------
# PaymentAdmin confirmed_total display
# ---------------------------------------------------------------------------


class PaymentAdminConfirmedTotalTest(TestCase):
    def setUp(self) -> None:
        from reservations.payments.admin import PaymentAdmin

        self.show = make_show(base_ticket_price=15)
        self.event = make_event(self.show)
        self.reservation = make_reservation(self.event)
        self.site = AdminSite()
        self.admin = PaymentAdmin(Payment, self.site)

    def _make_payment(self, total: Decimal, status: str) -> Payment:
        return make_payment(self.reservation, total=total, status=status)

    def test_confirmed_total_shows_amount_for_completed_payment(self) -> None:
        payment = self._make_payment(Decimal("30.00"), Payment.Status.COMPLETED)
        self.assertEqual(self.admin.confirmed_total(payment), "€ 30.00")

    def test_confirmed_total_shows_zero_for_pending_payment(self) -> None:
        payment = self._make_payment(Decimal("30.00"), Payment.Status.PENDING)
        self.assertEqual(self.admin.confirmed_total(payment), "€ 0.00")

    def test_confirmed_total_shows_zero_for_failed_payment(self) -> None:
        payment = self._make_payment(Decimal("30.00"), Payment.Status.FAILED)
        self.assertEqual(self.admin.confirmed_total(payment), "€ 0.00")

    def test_confirmed_total_shows_zero_for_refunded_payment(self) -> None:
        payment = self._make_payment(Decimal("30.00"), Payment.Status.REFUNDED)
        self.assertEqual(self.admin.confirmed_total(payment), "€ 0.00")


class PaymentAdminQueryCountTest(TestCase):
    def setUp(self) -> None:
        from reservations.payments.admin import PaymentAdmin

        self.show = make_show(base_ticket_price=15)
        self.event = make_event(self.show)
        self.admin = PaymentAdmin(Payment, AdminSite())

    def test_changelist_query_count_does_not_scale_with_rows(self) -> None:
        for i in range(3):
            reservation = make_reservation(self.event, email=f"r{i}@example.com")
            Guest.objects.create(reservation=reservation, first_name="A", last_name="B")
            make_payment(reservation, total=Decimal("15.00"))

        queryset = self.admin.get_queryset(RequestFactory().get("/"))
        with self.assertNumQueries(2):
            for payment in queryset:
                str(payment.reservation)
                payment.ticket_count()
                payment.event()
                _ = payment.ticket_price


# ---------------------------------------------------------------------------
# EventAdmin bulk and detail email actions
# ---------------------------------------------------------------------------

_EVENT_CHANGELIST_URL = "/mondmin/events/event/"


class EventAdminEmailActionsTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)
        self.superuser = User.objects.create_superuser("admin", "admin@example.com", "pass")
        self.client.force_login(self.superuser)

        # confirmed reservation
        self.confirmed_reservation = make_reservation(
            self.event, first_name="Anna", last_name="Smith", email="anna@example.com"
        )
        make_payment(self.confirmed_reservation)

        # unconfirmed reservation — should never be included
        waiting_reservation = make_reservation(self.event, email="pending@example.com")
        make_payment(waiting_reservation, status=Payment.Status.PENDING)

        mail.outbox.clear()

    def _bulk_post(self, action_name: str, **extra: Any) -> HttpResponse:
        return self.client.post(
            _EVENT_CHANGELIST_URL,
            {
                "action": action_name,
                "index": "0",
                "select_across": "0",
                "_selected_action": [str(self.event.pk)],
                **extra,
            },
        )

    def _detail_url(self) -> str:
        return f"/mondmin/events/event/{self.event.pk}/send-mail/"

    # --- print_reservations ---

    def test_print_reservations_returns_xlsx(self) -> None:
        response = self._bulk_post("print_reservations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(response.content[:2], b"PK")

    def test_print_reservations_excludes_unconfirmed(self) -> None:
        # Remove the confirmed payment so only the unconfirmed one exists
        Payment.objects.filter(reservation=self.confirmed_reservation).update(
            status=Payment.Status.PENDING
        )
        # Action still runs (returns empty sheet) without crashing
        response = self._bulk_post("print_reservations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[:2], b"PK")

    # --- send_to_reservants bulk action ---

    def test_bulk_send_to_reservants_shows_form(self) -> None:
        response = self._bulk_post("send_to_reservants")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subject")

    def test_bulk_send_to_reservants_only_confirmed_in_recipients(self) -> None:
        response = self._bulk_post("send_to_reservants")
        self.assertContains(response, "anna@example.com")
        self.assertNotContains(response, "pending@example.com")

    def test_bulk_send_to_reservants_preview(self) -> None:
        response = self._bulk_post(
            "send_to_reservants",
            text_field="Hello {{ firstname }}",
            subject="Test subject",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello Anna")

    def test_bulk_send_to_reservants_sends_to_confirmed_only(self) -> None:
        self._bulk_post(
            "send_to_reservants",
            text_field="Hello {{ firstname }}",
            subject="Test subject",
            send="Yes, Send mail",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("anna@example.com", mail.outbox[0].to[0])

    def test_bulk_send_to_reservants_redirects_after_send(self) -> None:
        response = self._bulk_post(
            "send_to_reservants",
            text_field="Hello",
            subject="Subject",
            send="Yes, Send mail",
        )
        self.assertEqual(response.status_code, 302)

    # --- send_mail_to_reservants_detail ---

    def test_detail_action_get_shows_form(self) -> None:
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subject")

    def test_detail_action_only_confirmed_in_recipients(self) -> None:
        response = self.client.get(self._detail_url())
        self.assertContains(response, "anna@example.com")
        self.assertNotContains(response, "pending@example.com")

    def test_detail_action_preview(self) -> None:
        response = self.client.post(
            self._detail_url(),
            {"text_field": "Hello {{ firstname }}", "subject": "Test subject"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello Anna")

    def test_detail_action_sends_to_confirmed_only(self) -> None:
        self.client.post(
            self._detail_url(),
            {
                "text_field": "Hello {{ firstname }}",
                "subject": "Test subject",
                "send": "Yes, Send mail",
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("anna@example.com", mail.outbox[0].to[0])

    def test_detail_action_redirects_after_send(self) -> None:
        response = self.client.post(
            self._detail_url(),
            {
                "text_field": "Hello",
                "subject": "Subject",
                "send": "Yes, Send mail",
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_detail_action_requires_login(self) -> None:
        self.client.logout()
        response = self.client.get(self._detail_url())
        self.assertNotEqual(response.status_code, 200)
