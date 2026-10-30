from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import stripe
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from events.models import Event
from reservations.models import Reservation
from reservations.payments.models import Payment
from reservations.tasks import (
    cleanup_abandoned_payments,
    refund_payment,
    send_confirmation_email,
    send_custom_email,
    send_refund_email,
)
from shows.models import Show


def make_image():
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    buf.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")


def make_banner_image():
    buf = BytesIO()
    Image.new("RGB", (400, 225), color="blue").save(buf, format="JPEG")
    buf.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile("banner.jpg", buf.read(), content_type="image/jpeg")


class CleanupAbandonedPaymentsTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(
            title="Test Show",
            description="",
            cast="",
            card_image=make_image(),
            banner_image=make_banner_image(),
            base_ticket_price=15,
        )
        base = timezone.now() + timedelta(days=7)
        self.event = Event.objects.create(
            show=self.show,
            admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=150,
            open_for_reservation=True,
        )
        self.reservation = Reservation.objects.create(
            event=self.event, first_name="Test", last_name="User", email="test@example.com"
        )

    def test_marks_pending_payments_older_than_48h_as_abandoned(self):
        # Create payment older than 48 hours
        old_payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        old_payment.created_at = timezone.now() - timedelta(hours=49)
        old_payment.save()

        # Create recent pending payment (should not be marked)
        recent_payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        count = cleanup_abandoned_payments()

        self.assertEqual(count, 1)
        old_payment.refresh_from_db()
        recent_payment.refresh_from_db()
        self.assertEqual(old_payment.status, Payment.Status.ABANDONED)
        self.assertEqual(recent_payment.status, Payment.Status.PENDING)

    def test_does_not_mark_completed_payments_as_abandoned(self):
        # Create old completed payment
        old_completed = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.COMPLETED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        old_completed.created_at = timezone.now() - timedelta(hours=49)
        old_completed.save()

        count = cleanup_abandoned_payments()

        self.assertEqual(count, 0)
        old_completed.refresh_from_db()
        self.assertEqual(old_completed.status, Payment.Status.COMPLETED)

    def test_does_not_mark_failed_payments_as_abandoned(self):
        # Create old failed payment
        old_failed = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.FAILED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        old_failed.created_at = timezone.now() - timedelta(hours=49)
        old_failed.save()

        count = cleanup_abandoned_payments()

        self.assertEqual(count, 0)
        old_failed.refresh_from_db()
        self.assertEqual(old_failed.status, Payment.Status.FAILED)

    def test_returns_zero_when_no_abandoned_payments(self):
        count = cleanup_abandoned_payments()
        self.assertEqual(count, 0)

    def test_payment_exactly_at_48h_boundary_is_marked(self):
        # Create payment exactly 48 hours old
        boundary_payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        boundary_payment.created_at = timezone.now() - timedelta(hours=48, seconds=1)
        boundary_payment.save()

        count = cleanup_abandoned_payments()

        self.assertEqual(count, 1)
        boundary_payment.refresh_from_db()
        self.assertEqual(boundary_payment.status, Payment.Status.ABANDONED)


class SendConfirmationEmailTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(
            title="Test Show",
            description="",
            cast="",
            card_image=make_image(),
            banner_image=make_banner_image(),
            base_ticket_price=15,
        )
        base = timezone.now() + timedelta(days=7)
        self.event = Event.objects.create(
            show=self.show,
            admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=150,
            open_for_reservation=True,
        )
        self.reservation = Reservation.objects.create(
            event=self.event, first_name="Test", last_name="User", email="test@example.com"
        )
        Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.COMPLETED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        # Clear mail outbox after setup (signal fires on Payment creation)
        mail.outbox.clear()

    def test_sends_confirmation_email(self):
        send_confirmation_email(str(self.reservation.id))

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Test Show", email.subject)
        self.assertEqual(email.to, ["test@example.com"])
        self.assertIn("Test", email.body)

    def test_handles_nonexistent_reservation(self):
        with self.assertLogs("reservations.tasks", level="ERROR") as logs:
            send_confirmation_email("00000000-0000-0000-0000-000000000000")

        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any("not found" in log for log in logs.output))

    def test_email_contains_payment_details(self):
        send_confirmation_email(str(self.reservation.id))

        email = mail.outbox[0]
        self.assertIn("15.00 EUR", email.body)
        self.assertIn("30.00 EUR", email.body)

    @patch("reservations.emails.send_confirmation_mail")
    def test_task_raises_on_email_error(self, mock_send):
        mock_send.side_effect = Exception("Email service down")

        with self.assertRaises(Exception):
            send_confirmation_email(str(self.reservation.id))


class SendRefundEmailTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(
            title="Test Show",
            description="",
            cast="",
            card_image=make_image(),
            banner_image=make_banner_image(),
            base_ticket_price=15,
        )
        base = timezone.now() + timedelta(days=7)
        self.event = Event.objects.create(
            show=self.show,
            admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=150,
            open_for_reservation=True,
        )
        self.reservation = Reservation.objects.create(
            event=self.event, first_name="Test", last_name="User", email="test@example.com"
        )
        Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.REFUNDED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        # Clear mail outbox after setup (signal fires on Payment creation)
        mail.outbox.clear()

    def test_sends_refund_email(self):
        send_refund_email(str(self.reservation.id))

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Refunded", email.subject)
        self.assertEqual(email.to, ["test@example.com"])
        self.assertIn("30.00 EUR", email.body)

    def test_handles_nonexistent_reservation(self):
        with self.assertLogs("reservations.tasks", level="ERROR") as logs:
            send_refund_email("00000000-0000-0000-0000-000000000000")

        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any("not found" in log for log in logs.output))

    @patch("reservations.emails.send_refund_mail")
    def test_task_raises_on_email_error(self, mock_send):
        mock_send.side_effect = Exception("Email service down")

        with self.assertRaises(Exception):
            send_refund_email(str(self.reservation.id))


@override_settings(STRIPE_SECRET_KEY="sk_test_expected")
class RefundPaymentTaskTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(
            title="Test Show",
            description="",
            cast="",
            card_image=make_image(),
            banner_image=make_banner_image(),
            base_ticket_price=15,
        )
        base = timezone.now() + timedelta(days=7)
        self.event = Event.objects.create(
            show=self.show,
            admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=150,
            open_for_reservation=True,
        )
        self.reservation = Reservation.objects.create(
            event=self.event, first_name="Test", last_name="User", email="test@example.com"
        )
        self.payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.COMPLETED,
            stripe_payment_intent_id="pi_test_123",
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        # Clear confirmation email queued by the COMPLETED payment signal.
        mail.outbox.clear()

    @patch("reservations.tasks.send_refund_email.delay")
    @patch("reservations.tasks.stripe.Refund.create")
    def test_refunds_completed_payment_and_marks_it_refunded(self, mock_refund, mock_email):
        refund_payment(str(self.payment.pk))

        self.assertEqual(stripe.api_key, "sk_test_expected")
        mock_refund.assert_called_once_with(
            payment_intent="pi_test_123",
            idempotency_key=f"refund-{self.payment.pk}",
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)
        mock_email.assert_called_once_with(str(self.reservation.id))

    @patch("reservations.tasks.stripe.Refund.create")
    def test_skips_payment_without_payment_intent(self, mock_refund):
        for missing_intent in (None, ""):
            with self.subTest(missing_intent=missing_intent):
                Payment.objects.filter(pk=self.payment.pk).update(
                    status=Payment.Status.COMPLETED,
                    stripe_payment_intent_id=missing_intent,
                )

                with self.assertLogs("reservations.tasks", level="ERROR") as logs:
                    refund_payment(str(self.payment.pk))

                mock_refund.assert_not_called()
                self.payment.refresh_from_db()
                self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
                self.assertTrue(
                    any("missing Stripe PaymentIntent ID" in line for line in logs.output)
                )

    @patch("reservations.tasks.stripe.Refund.create")
    def test_skips_payment_not_completed(self, mock_refund):
        Payment.objects.filter(pk=self.payment.pk).update(status=Payment.Status.PENDING)

        refund_payment(str(self.payment.pk))

        mock_refund.assert_not_called()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    @patch("reservations.tasks.stripe.Refund.create")
    def test_handles_missing_payment(self, mock_refund):
        with self.assertLogs("reservations.tasks", level="ERROR") as logs:
            refund_payment("00000000-0000-0000-0000-000000000000")

        mock_refund.assert_not_called()
        self.assertTrue(any("not found" in line for line in logs.output))

    @patch("reservations.tasks.stripe.Refund.create")
    def test_does_not_retry_invalid_request(self, mock_refund):
        mock_refund.side_effect = stripe.InvalidRequestError("cannot refund", param=None)

        with self.assertLogs("reservations.tasks", level="ERROR") as logs:
            refund_payment(str(self.payment.pk))

        mock_refund.assert_called_once()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
        self.assertTrue(any("failed permanently" in line for line in logs.output))


class SendCustomEmailTest(TestCase):
    @override_settings(DEFAULT_FROM_EMAIL="noreply@zirkusmond.test")
    def test_sends_email_from_default_from_address(self):
        send_custom_email("Anna Muster", "anna@example.com", "Hallo", "Body text")

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.from_email, "noreply@zirkusmond.test")
        self.assertEqual(email.to, ["Anna Muster <anna@example.com>"])
        self.assertEqual(email.subject, "Hallo")
        self.assertEqual(email.body, "Body text")

    def test_quotes_names_with_special_characters(self):
        send_custom_email("Muster, Anna", "anna@example.com", "Hallo", "Body")

        self.assertEqual(mail.outbox[0].to, ['"Muster, Anna" <anna@example.com>'])

    @patch("reservations.emails.send_custom_mail")
    def test_task_raises_on_email_error(self, mock_send):
        mock_send.side_effect = Exception("Email service down")

        with self.assertRaises(Exception):
            send_custom_email("Anna", "anna@example.com", "Hallo", "Body")


class PaymentSignalsTest(TestCase):
    def setUp(self):
        self.show = Show.objects.create(
            title="Test Show",
            description="",
            cast="",
            card_image=make_image(),
            banner_image=make_banner_image(),
            base_ticket_price=15,
        )
        base = timezone.now() + timedelta(days=7)
        self.event = Event.objects.create(
            show=self.show,
            admission=base.replace(hour=19, minute=0, second=0, microsecond=0),
            begin=base.replace(hour=20, minute=0, second=0, microsecond=0),
            reservation_capacity=150,
            open_for_reservation=True,
        )
        self.reservation = Reservation.objects.create(
            event=self.event, first_name="Test", last_name="User", email="test@example.com"
        )

    @patch("reservations.tasks.send_confirmation_email.delay")
    def test_signal_queues_confirmation_email_on_payment_completed(self, mock_task):
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        payment.status = Payment.Status.COMPLETED
        payment.save()

        mock_task.assert_called_once_with(str(self.reservation.id))

    @patch("reservations.tasks.send_refund_email.delay")
    def test_signal_queues_refund_email_on_payment_refunded(self, mock_task):
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.COMPLETED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        payment.status = Payment.Status.REFUNDED
        payment.save()

        mock_task.assert_called_once_with(str(self.reservation.id))

    @patch("reservations.tasks.send_confirmation_email.delay")
    def test_signal_does_not_queue_email_on_failed_payment(self, mock_task):
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        payment.status = Payment.Status.FAILED
        payment.save()

        mock_task.assert_not_called()

    @patch("reservations.tasks.send_confirmation_email.delay")
    @patch("reservations.tasks.send_refund_email.delay")
    def test_signal_does_not_queue_email_when_payment_has_no_reservation(
        self, mock_refund, mock_confirmation
    ):
        payment = Payment.objects.create(
            reservation=None,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        payment.status = Payment.Status.COMPLETED
        payment.save()

        mock_confirmation.assert_not_called()
        mock_refund.assert_not_called()

    def test_eager_mode_sends_confirmation_email_immediately(self):
        # In test settings, CELERY_TASK_ALWAYS_EAGER should be True
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.PENDING,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )

        payment.status = Payment.Status.COMPLETED
        payment.save()

        # Email should be sent immediately in eager mode
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Test Show", mail.outbox[0].subject)

    def test_eager_mode_sends_refund_email_immediately(self):
        payment = Payment.objects.create(
            reservation=self.reservation,
            status=Payment.Status.COMPLETED,
            total=Decimal("30.00"),
            custom_ticket_price=15,
        )
        # Clear confirmation email from COMPLETED status
        mail.outbox.clear()

        payment.status = Payment.Status.REFUNDED
        payment.save()

        # Email should be sent immediately in eager mode
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Refunded", mail.outbox[0].subject)
