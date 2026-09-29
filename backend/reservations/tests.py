from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Count
from django.test import RequestFactory, TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from events.models import Event
from newsletter.models import NewsletterSubscription
from reservations.admin import GuestAdmin, ReservationAdmin
from reservations.models import Guest, Reservation
from reservations.payments.models import Payment
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


def make_event(show: Show, offset_days: int = 7, capacity: int = 150) -> Event:
    base = timezone.now() + timedelta(days=offset_days)
    return Event.objects.create(
        show=show,
        admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
        begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
        reservation_capacity=capacity,
        open_for_reservation=True,
    )


def make_reservation(event: Event, **kwargs: Any) -> Reservation:
    defaults = dict(first_name="Test", last_name="User", email="test@example.com")
    defaults.update(kwargs)
    return Reservation.objects.create(event=event, **defaults)


# ---------------------------------------------------------------------------
# Reservation model
# ---------------------------------------------------------------------------


class ReservationModelTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)
        self.reservation = make_reservation(self.event)

    def test_ticket_count_no_guests(self) -> None:
        self.assertEqual(self.reservation.ticket_count(), 1)

    def test_ticket_count_with_guests(self) -> None:
        Guest.objects.create(reservation=self.reservation, first_name="G", last_name="H")
        Guest.objects.create(reservation=self.reservation, first_name="I", last_name="J")
        self.assertEqual(self.reservation.ticket_count(), 3)

    def test_str_contains_event_and_name(self) -> None:
        result = str(self.reservation)
        self.assertIn("User", result)
        self.assertIn("Test", result)

    def test_guests_relation(self) -> None:
        guest = Guest.objects.create(reservation=self.reservation, first_name="G", last_name="H")
        self.assertIn(guest, self.reservation.guests.all())

    def test_checked_in_defaults_false(self) -> None:
        self.assertFalse(self.reservation.checked_in)

    def test_uuid_primary_key(self) -> None:
        self.assertIsNotNone(self.reservation.id)
        self.assertIsInstance(str(self.reservation.id), str)

    def test_ticket_count_uses_annotated_guest_count_without_query(self) -> None:
        Guest.objects.create(reservation=self.reservation, first_name="G", last_name="H")
        annotated = Reservation.objects.annotate(
            annotated_guest_count=Count("guests", distinct=True)
        ).get(pk=self.reservation.pk)

        with self.assertNumQueries(0):
            self.assertEqual(annotated.ticket_count(), 2)


# ---------------------------------------------------------------------------
# Guest model
# ---------------------------------------------------------------------------


class GuestModelTest(TestCase):
    def setUp(self) -> None:
        show = make_show()
        event = make_event(show)
        self.reservation = make_reservation(event)

    def test_ticket_id_auto_assigned(self) -> None:
        guest = Guest.objects.create(reservation=self.reservation, first_name="A", last_name="B")
        self.assertIsNotNone(guest.ticket_id)

    def test_ticket_ids_unique(self) -> None:
        g1 = Guest.objects.create(reservation=self.reservation, first_name="A", last_name="B")
        g2 = Guest.objects.create(reservation=self.reservation, first_name="C", last_name="D")
        self.assertNotEqual(g1.ticket_id, g2.ticket_id)

    def test_ticket_id_can_be_null(self) -> None:
        guest = Guest.objects.create(
            reservation=self.reservation, first_name="Old", last_name="Guest"
        )
        guest.ticket_id = None
        guest.save()
        guest.refresh_from_db()
        self.assertIsNone(guest.ticket_id)

    def test_checked_in_defaults_false(self) -> None:
        guest = Guest.objects.create(reservation=self.reservation, first_name="A", last_name="B")
        self.assertFalse(guest.checked_in)

    def test_str_contains_name(self) -> None:
        guest = Guest.objects.create(
            reservation=self.reservation, first_name="Alice", last_name="Smith"
        )
        self.assertIn("Alice", str(guest))
        self.assertIn("Smith", str(guest))

    def test_deleting_reservation_cascades_to_guests(self) -> None:
        guest = Guest.objects.create(reservation=self.reservation, first_name="A", last_name="B")
        guest_id = guest.pk
        self.reservation.delete()
        self.assertFalse(Guest.objects.filter(pk=guest_id).exists())


# ---------------------------------------------------------------------------
# Reserve API view
# ---------------------------------------------------------------------------


class ReserveAPIViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.show = make_show()
        self.event = make_event(self.show)

    def _url(self, show_id: int | None = None) -> str:
        pk = show_id if show_id is not None else self.show.pk
        return f"/reservation/{pk}"

    def _post_data(self, **overrides: Any) -> dict[str, Any]:
        data = {
            "event_id": self.event.pk,
            "first_name": "Anna",
            "last_name": "Doe",
            "email": "anna@example.com",
            "attendee_count": 1,
        }
        data.update(overrides)
        return data

    # -----------------------------------------------------------------------
    # Successful reservation — no guests, no newsletter
    # -----------------------------------------------------------------------

    def test_valid_post_returns_201(self) -> None:
        response = self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(response.status_code, 201)

    def test_valid_post_creates_reservation(self) -> None:
        self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(Reservation.objects.count(), 1)

    def test_valid_post_response_contains_reservation_id(self) -> None:
        response = self.client.post(self._url(), self._post_data(), format="json")
        reservation = Reservation.objects.first()
        self.assertIn("reservation_id", response.data)
        self.assertEqual(str(response.data["reservation_id"]), str(reservation.id))

    def test_valid_post_does_not_create_guests(self) -> None:
        self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(Guest.objects.count(), 0)

    # -----------------------------------------------------------------------
    # Reservation with guests
    # -----------------------------------------------------------------------

    def test_post_with_guests_creates_guest_records(self) -> None:
        data = self._post_data(
            attendee_count=3,
            guests=[
                {"first_name": "Bob", "last_name": "Smith"},
                {"first_name": "Carol", "last_name": "Jones"},
            ],
        )
        self.client.post(self._url(), data, format="json")
        self.assertEqual(Guest.objects.count(), 2)

    def test_post_with_guests_links_guests_to_reservation(self) -> None:
        data = self._post_data(
            attendee_count=2,
            guests=[{"first_name": "Bob", "last_name": "Smith"}],
        )
        self.client.post(self._url(), data, format="json")
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.guests.count(), 1)

    # -----------------------------------------------------------------------
    # Newsletter opt-in
    # -----------------------------------------------------------------------

    def test_newsletter_flag_true_registers_email(self) -> None:
        self.client.post(self._url(), self._post_data(newsletter=True), format="json")
        self.assertTrue(
            NewsletterSubscription.objects.filter(email="anna@example.com").exists(),
            "Expected a NewsletterSubscription record for the submitted email.",
        )

    def test_newsletter_flag_false_does_not_register_email(self) -> None:
        self.client.post(self._url(), self._post_data(newsletter=False), format="json")
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    def test_newsletter_flag_absent_does_not_register_email(self) -> None:
        # newsletter defaults to False; omitting it must not create a record.
        self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

    # -----------------------------------------------------------------------
    # Serializer validation failures — expected 400
    # -----------------------------------------------------------------------

    def test_missing_required_fields_returns_400(self) -> None:
        response = self.client.post(self._url(), {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_first_name_returns_400(self) -> None:
        data = self._post_data()
        del data["first_name"]
        response = self.client.post(self._url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_email_returns_400(self) -> None:
        data = self._post_data()
        del data["email"]
        response = self.client.post(self._url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_attendee_count_returns_400(self) -> None:
        data = self._post_data()
        del data["attendee_count"]
        response = self.client.post(self._url(), data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_serializer_data_creates_no_db_records(self) -> None:
        self.client.post(self._url(), {}, format="json")
        self.assertEqual(Reservation.objects.count(), 0)

    # -----------------------------------------------------------------------
    # Closed event — expected 400
    # -----------------------------------------------------------------------

    def test_closed_event_returns_400(self) -> None:
        self.event.open_for_reservation = False
        self.event.save()
        response = self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(response.status_code, 400)

    def test_closed_event_returns_error_key(self) -> None:
        self.event.open_for_reservation = False
        self.event.save()
        response = self.client.post(self._url(), self._post_data(), format="json")
        self.assertIn("error", response.data)

    def test_closed_event_creates_no_db_records(self) -> None:
        self.event.open_for_reservation = False
        self.event.save()
        self.client.post(self._url(), self._post_data(), format="json")
        self.assertEqual(Reservation.objects.count(), 0)

    # -----------------------------------------------------------------------
    # Custom price validation
    # -----------------------------------------------------------------------
    # make_show() sets base_ticket_price=15; effective range is [5, 25]
    # (max(5, 15-10) to 15+10).

    def test_invalid_custom_price_below_minimum_returns_400(self) -> None:
        # Price 1 is below the minimum of 5.
        response = self.client.post(self._url(), self._post_data(custom_price=1), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_custom_price_above_maximum_returns_400(self) -> None:
        # Price 99 is above the maximum of 25.
        response = self.client.post(self._url(), self._post_data(custom_price=99), format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_custom_price_returns_error_key(self) -> None:
        response = self.client.post(self._url(), self._post_data(custom_price=1), format="json")
        self.assertIn("error", response.data)

    def test_invalid_custom_price_creates_no_db_records(self) -> None:
        self.client.post(self._url(), self._post_data(custom_price=1), format="json")
        self.assertEqual(Reservation.objects.count(), 0)

    def test_valid_custom_price_returns_201(self) -> None:
        response = self.client.post(self._url(), self._post_data(custom_price=20), format="json")
        self.assertEqual(response.status_code, 201)

    # -----------------------------------------------------------------------
    # 404 cases
    # -----------------------------------------------------------------------

    def test_nonexistent_show_returns_404(self) -> None:
        response = self.client.post(self._url(show_id=99999), self._post_data(), format="json")
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_event_returns_404(self) -> None:
        # event_id 99999 does not exist in the database.
        data = self._post_data(event_id=99999)
        response = self.client.post(self._url(), data, format="json")
        self.assertEqual(response.status_code, 404)

    def test_event_belonging_to_different_show_returns_404(self) -> None:
        # An event that exists but belongs to a different show must not be
        # accessible through this show's URL.
        other_show = make_show()
        other_event = make_event(other_show)
        data = self._post_data(event_id=other_event.pk)
        response = self.client.post(self._url(), data, format="json")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# ReservationAdmin — re-send confirmation mail when a reservation is moved
# to a different event
# ---------------------------------------------------------------------------


class _StubForm:
    """Minimal stand-in for the admin ModelForm: only ``changed_data`` matters."""

    def __init__(self, changed_data: list[str]) -> None:
        self.changed_data = changed_data


class ReservationAdminRescheduleEmailTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.old_event = make_event(self.show, offset_days=7)
        self.new_event = make_event(self.show, offset_days=14)
        self.reservation = make_reservation(self.old_event, email="guest@example.com")
        self.admin = ReservationAdmin(Reservation, AdminSite())
        self.user = User.objects.create_superuser("admin", "admin@example.com", "pw")
        mail.outbox.clear()

    def _request(self) -> Any:
        request = RequestFactory().post("/")
        request.user = self.user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def _pay(self, status: str = Payment.Status.COMPLETED) -> Payment:
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=status,
            total=Decimal("15.00"),
            custom_ticket_price=15,
        )
        # a COMPLETED payment triggers its own confirmation mail via the
        # post_save signal on Payment — drop it so the outbox only reflects
        # what save_model does.
        mail.outbox.clear()
        return payment

    def _save(self, changed_fields: list[str], *, change: bool = True) -> Any:
        request = self._request()
        self.admin.save_model(request, self.reservation, _StubForm(changed_fields), change)
        return request

    def test_paid_reservation_event_change_sends_mail(self) -> None:
        self._pay()
        self.reservation.event = self.new_event
        self._save(["event"])

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["guest@example.com"])
        self.assertIn(self.show.title, sent.subject)
        self.assertEqual(len(sent.attachments), 1)

    def test_mail_reflects_new_event_date_not_old(self) -> None:
        self._pay()
        self.reservation.event = self.new_event
        self._save(["event"])

        body = mail.outbox[0].body
        self.assertIn(self.new_event.date_str(), body)
        self.assertNotIn(self.old_event.date_str(), body)

    def test_admin_gets_success_message(self) -> None:
        self._pay()
        self.reservation.event = self.new_event
        request = self._save(["event"])

        levels = [m.level for m in request._messages]
        self.assertIn(messages.INFO, levels)

    def test_no_mail_when_event_field_not_changed(self) -> None:
        self._pay()
        self._save(["checked_in"])
        self.assertEqual(mail.outbox, [])

    def test_no_mail_when_reservation_has_no_completed_payment(self) -> None:
        self._pay(status=Payment.Status.PENDING)
        self.reservation.event = self.new_event
        self._save(["event"])
        self.assertEqual(mail.outbox, [])

    def test_no_mail_when_reservation_has_no_payment_at_all(self) -> None:
        self.reservation.event = self.new_event
        self._save(["event"])
        self.assertEqual(mail.outbox, [])

    def test_no_mail_on_create(self) -> None:
        self._pay()
        self._save(["event"], change=False)
        self.assertEqual(mail.outbox, [])

    def test_no_mail_and_no_crash_when_event_cleared(self) -> None:
        self._pay()
        self.reservation.event = None
        self._save(["event"])
        self.assertEqual(mail.outbox, [])

    def test_send_failure_is_reported_and_not_raised(self) -> None:
        self._pay()
        self.reservation.event = self.new_event
        with patch(
            "reservations.emails.send_confirmation_mail",
            side_effect=RuntimeError("smtp down"),
        ):
            request = self._save(["event"])

        error_levels = [m.level for m in request._messages if m.level == messages.ERROR]
        self.assertEqual(len(error_levels), 1)


# ---------------------------------------------------------------------------
# Admin changelist query counts (N+1 regression guards)
# ---------------------------------------------------------------------------


class ReservationAdminQueryCountTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)
        self.admin = ReservationAdmin(Reservation, AdminSite())

    def _request(self) -> Any:
        request = RequestFactory().get("/")
        request.resolver_match = SimpleNamespace(url_name="reservation_changelist")
        return request

    def test_changelist_query_count_does_not_scale_with_guests(self) -> None:
        for i in range(3):
            reservation = make_reservation(self.event, email=f"r{i}@example.com")
            Guest.objects.create(reservation=reservation, first_name="A", last_name="B")
            Guest.objects.create(reservation=reservation, first_name="C", last_name="D")

        queryset = self.admin.get_queryset(self._request())
        with self.assertNumQueries(1):
            for reservation in queryset:
                str(reservation)
                reservation.ticket_count()


class GuestAdminQueryCountTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)
        self.admin = GuestAdmin(Guest, AdminSite())

    def test_changelist_query_count_does_not_scale_with_reservations(self) -> None:
        for i in range(3):
            reservation = make_reservation(self.event, email=f"r{i}@example.com")
            Guest.objects.create(reservation=reservation, first_name="A", last_name="B")
            Guest.objects.create(reservation=reservation, first_name="C", last_name="D")

        queryset = self.admin.get_queryset(RequestFactory().get("/"))
        with self.assertNumQueries(2):
            for guest in queryset:
                str(guest.reservation)
