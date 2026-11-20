import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from events.models import Event
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
# QR scanner views
# ---------------------------------------------------------------------------


class QrScannerViewTest(TestCase):
    def setUp(self) -> None:
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)

    def test_get_events_requires_staff(self) -> None:
        response = self.client.get("/qr-scanner/get-events")
        self.assertEqual(response.status_code, 403)

    def test_get_events_returns_json(self) -> None:
        self.client.force_login(self.staff)
        show = make_show()
        make_event(show)
        response = self.client.get("/qr-scanner/get-events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertIn("title", data[0])

    def test_get_events_excludes_past_events(self) -> None:
        self.client.force_login(self.staff)
        show = make_show()
        make_event(show, offset_days=-5)
        response = self.client.get("/qr-scanner/get-events")
        self.assertEqual(response.json(), [])


# ---------------------------------------------------------------------------
# Check-in view
# ---------------------------------------------------------------------------


class CheckInViewTest(TestCase):
    def setUp(self) -> None:
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(self.staff)

        show = make_show()
        event = make_event(show)
        self.reservation = make_reservation(event)
        self.guest = Guest.objects.create(
            reservation=self.reservation, first_name="Guest", last_name="One"
        )

    def _url(self, ticket_id: uuid.UUID) -> str:
        return f"/qr-scanner/{ticket_id}/check-in"

    def test_check_in_by_reservation_id(self) -> None:
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.reservation.refresh_from_db()
        self.assertTrue(self.reservation.checked_in)

    def test_check_in_by_guest_ticket_id(self) -> None:
        response = self.client.post(self._url(self.guest.ticket_id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.checked_in)

    def test_guest_check_in_does_not_affect_reservation(self) -> None:
        self.client.post(self._url(self.guest.ticket_id))
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)

    def test_already_checked_in_reservation_returns_400(self) -> None:
        self.reservation.checked_in = True
        self.reservation.save()
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("already checked in", response.json()["error"])

    def test_already_checked_in_guest_returns_400(self) -> None:
        self.guest.checked_in = True
        self.guest.save()
        response = self.client.post(self._url(self.guest.ticket_id))
        self.assertEqual(response.status_code, 400)
        self.assertIn("already checked in", response.json()["error"])

    def test_unknown_uuid_returns_404(self) -> None:
        response = self.client.post(self._url(uuid.uuid4()))
        self.assertEqual(response.status_code, 404)

    def test_reservation_check_in_returns_is_group_true(self) -> None:
        response = self.client.post(self._url(self.reservation.id))
        self.assertTrue(response.json().get("is_group"))

    def test_response_includes_guest_names(self) -> None:
        response = self.client.post(self._url(self.reservation.id))
        names = response.json()["guests"]
        self.assertTrue(any("Test" in name for name in names))

    def _make_payment(self, status: str) -> Payment:
        payment = Payment.objects.create(
            payment_method=Payment.PaymentMethod.CARD,
            reservation=self.reservation,
            custom_ticket_price=20,
            total=Decimal("20"),
            status=status,
        )
        return payment

    def test_failed_payment_blocks_reservation_check_in(self) -> None:
        self._make_payment(Payment.Status.FAILED)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("failed", response.json()["error"].lower())

    def test_failed_payment_blocks_guest_check_in(self) -> None:
        self._make_payment(Payment.Status.FAILED)
        response = self.client.post(self._url(self.guest.ticket_id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("failed", response.json()["error"].lower())

    def test_failed_payment_does_not_mark_checked_in(self) -> None:
        self._make_payment(Payment.Status.FAILED)
        self.client.post(self._url(self.reservation.id))
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)

    def test_completed_payment_allows_check_in(self) -> None:
        self._make_payment(Payment.Status.COMPLETED)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_refunded_payment_blocks_reservation_check_in(self) -> None:
        self._make_payment(Payment.Status.REFUNDED)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("refund", response.json()["error"].lower())

    def test_refunded_payment_blocks_guest_check_in(self) -> None:
        self._make_payment(Payment.Status.REFUNDED)
        response = self.client.post(self._url(self.guest.ticket_id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("refund", response.json()["error"].lower())

    def test_refunded_payment_does_not_mark_checked_in(self) -> None:
        self._make_payment(Payment.Status.REFUNDED)
        self.client.post(self._url(self.reservation.id))
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)

    def test_no_payment_allows_check_in(self) -> None:
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_abandoned_payment_blocks_reservation_check_in(self) -> None:
        self._make_payment(Payment.Status.ABANDONED)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("not completed", response.json()["error"])

    def test_abandoned_payment_blocks_guest_check_in(self) -> None:
        self._make_payment(Payment.Status.ABANDONED)
        response = self.client.post(self._url(self.guest.ticket_id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("not completed", response.json()["error"])

    def test_abandoned_payment_does_not_mark_checked_in(self) -> None:
        self._make_payment(Payment.Status.ABANDONED)
        self.client.post(self._url(self.reservation.id))
        self.client.post(self._url(self.guest.ticket_id))
        self.reservation.refresh_from_db()
        self.guest.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)
        self.assertFalse(self.guest.checked_in)

    def test_pending_payment_blocks_check_in(self) -> None:
        self._make_payment(Payment.Status.PENDING)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 402)
        self.assertIn("not completed", response.json()["error"])

    def test_completed_payment_with_later_abandoned_attempt_allows_check_in(self) -> None:
        self._make_payment(Payment.Status.COMPLETED)
        self._make_payment(Payment.Status.ABANDONED)
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])


# ---------------------------------------------------------------------------
# Check-in view — ?event=<id> scoping
# ---------------------------------------------------------------------------


class CheckInEventScopeTest(TestCase):
    def setUp(self) -> None:
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(self.staff)

        show = make_show()
        self.event = make_event(show, offset_days=7)
        self.other_event = make_event(show, offset_days=14)
        self.reservation = make_reservation(self.event)
        self.guest = Guest.objects.create(
            reservation=self.reservation, first_name="Guest", last_name="One"
        )

    def _url(self, ticket_id: uuid.UUID, event_id: int | str | None = None) -> str:
        url = f"/qr-scanner/{ticket_id}/check-in"
        if event_id is not None:
            url += f"?event={event_id}"
        return url

    # --- matching / absent / unparsable event param: check-in proceeds ---

    def test_matching_event_allows_reservation_check_in(self) -> None:
        response = self.client.post(self._url(self.reservation.id, self.event.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_matching_event_allows_guest_check_in(self) -> None:
        response = self.client.post(self._url(self.guest.ticket_id, self.event.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_absent_event_param_still_checks_in(self) -> None:
        response = self.client.post(self._url(self.reservation.id))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_non_numeric_event_param_is_ignored(self) -> None:
        response = self.client.post(self._url(self.reservation.id, "abc"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    # --- wrong event: 409, nobody checked in ---

    def test_wrong_event_rejects_reservation(self) -> None:
        response = self.client.post(self._url(self.reservation.id, self.other_event.id))
        self.assertEqual(response.status_code, 409)
        self.assertIn("different event", response.json()["error"])

    def test_wrong_event_does_not_check_in_reservation(self) -> None:
        self.client.post(self._url(self.reservation.id, self.other_event.id))
        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)

    def test_wrong_event_rejects_guest(self) -> None:
        response = self.client.post(self._url(self.guest.ticket_id, self.other_event.id))
        self.assertEqual(response.status_code, 409)
        self.assertIn("different event", response.json()["error"])

    def test_wrong_event_does_not_check_in_guest(self) -> None:
        self.client.post(self._url(self.guest.ticket_id, self.other_event.id))
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.checked_in)

    def test_wrong_event_response_includes_guest_names(self) -> None:
        response = self.client.post(self._url(self.reservation.id, self.other_event.id))
        self.assertTrue(any("Guest" in name for name in response.json()["guests"]))

    def test_unknown_ticket_with_event_returns_404_not_409(self) -> None:
        response = self.client.post(self._url(uuid.uuid4(), self.event.id))
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["error"].lower())


# ---------------------------------------------------------------------------
# Rescheduled reservation — old-event QR fails, new-event QR checks in,
# for the reservant AND every guest
# ---------------------------------------------------------------------------


class RescheduledReservationCheckInTest(TestCase):
    def setUp(self) -> None:
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(self.staff)

        show = make_show()
        self.old_event = make_event(show, offset_days=7)
        self.new_event = make_event(show, offset_days=21)
        self.reservation = make_reservation(self.old_event)
        self.guests = [
            Guest.objects.create(
                reservation=self.reservation, first_name=f"Guest{i}", last_name="X"
            )
            for i in range(3)
        ]

        # staff moves the booking to another event
        self.reservation.event = self.new_event
        self.reservation.save()

    def _check_in(self, ticket_id: uuid.UUID, event_id: int) -> Any:
        return self.client.post(f"/qr-scanner/{ticket_id}/check-in?event={event_id}")

    def _all_ticket_ids(self) -> list[uuid.UUID]:
        return [self.reservation.id, *(g.ticket_id for g in self.guests)]

    def test_old_event_qr_rejected_for_reservant_and_every_guest(self) -> None:
        for ticket_id in self._all_ticket_ids():
            response = self._check_in(ticket_id, self.old_event.id)
            self.assertEqual(response.status_code, 409, msg=f"ticket {ticket_id}")
            self.assertIn("different event", response.json()["error"])

    def test_old_event_qr_checks_in_nobody(self) -> None:
        for ticket_id in self._all_ticket_ids():
            self._check_in(ticket_id, self.old_event.id)

        self.reservation.refresh_from_db()
        self.assertFalse(self.reservation.checked_in)
        for guest in self.guests:
            guest.refresh_from_db()
            self.assertFalse(guest.checked_in)

    def test_new_event_qr_checks_in_reservant_and_every_guest(self) -> None:
        for ticket_id in self._all_ticket_ids():
            response = self._check_in(ticket_id, self.new_event.id)
            self.assertEqual(response.status_code, 200, msg=f"ticket {ticket_id}")
            self.assertTrue(response.json()["success"])

        self.reservation.refresh_from_db()
        self.assertTrue(self.reservation.checked_in)
        for guest in self.guests:
            guest.refresh_from_db()
            self.assertTrue(guest.checked_in)
