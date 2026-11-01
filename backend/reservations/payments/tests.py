import json as _json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

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
# Payment model
# ---------------------------------------------------------------------------


class PaymentCreateForReservationTest(TestCase):
    def setUp(self) -> None:
        self.show = make_show(base_ticket_price=20, min_ticket_price=10, max_ticket_price=30)
        self.event = make_event(self.show)
        self.reservation = make_reservation(self.event)

    def test_creates_payment_with_valid_price(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=20, payment_method="card"
        )
        self.assertIsNotNone(payment.pk)
        self.assertEqual(payment.custom_ticket_price, 20)
        self.assertEqual(payment.reservation, self.reservation)

    def test_total_is_ticket_count_times_price(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=20, payment_method="card"
        )
        self.assertEqual(payment.total, Decimal("20"))

    def test_total_includes_guests(self) -> None:
        Guest.objects.create(reservation=self.reservation, first_name="G", last_name="H")
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=15, payment_method="card"
        )
        self.assertEqual(payment.total, Decimal("30"))

    def test_price_at_minimum_boundary_is_accepted(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=10, payment_method="card"
        )
        self.assertEqual(payment.custom_ticket_price, 10)

    def test_price_at_maximum_boundary_is_accepted(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=30, payment_method="card"
        )
        self.assertEqual(payment.custom_ticket_price, 30)

    def test_none_price_raises(self) -> None:
        with self.assertRaises(ValueError):
            Payment.create_for_reservation(
                self.reservation, custom_ticket_price=None, payment_method="card"
            )

    def test_price_below_minimum_raises(self) -> None:
        with self.assertRaises(ValueError):
            Payment.create_for_reservation(
                self.reservation, custom_ticket_price=9, payment_method="card"
            )

    def test_price_above_maximum_raises(self) -> None:
        with self.assertRaises(ValueError):
            Payment.create_for_reservation(
                self.reservation, custom_ticket_price=31, payment_method="card"
            )

    def test_status_defaults_to_pending(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=20, payment_method="card"
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_creates_payment_with_paypal(self) -> None:
        payment = Payment.create_for_reservation(
            self.reservation, custom_ticket_price=20, payment_method="paypal"
        )
        self.assertIsNotNone(payment.pk)
        self.assertEqual(payment.payment_method, "paypal")
        self.assertEqual(payment.custom_ticket_price, 20)

    def test_payment_method_card_value(self) -> None:
        self.assertEqual(Payment.PaymentMethod.CARD, "card")

    def test_payment_method_paypal_value(self) -> None:
        self.assertEqual(Payment.PaymentMethod.PAYPAL, "paypal")


# ---------------------------------------------------------------------------
# Payment URL methods
# ---------------------------------------------------------------------------


class PaymentURLTest(TestCase):
    def setUp(self) -> None:
        show = make_show(base_ticket_price=20, min_ticket_price=10, max_ticket_price=30)
        event = make_event(show)
        reservation = make_reservation(event)
        self.payment = Payment.objects.create(
            payment_method=Payment.PaymentMethod.CARD,
            reservation=reservation,
            custom_ticket_price=20,
            total=Decimal("20"),
        )

    @override_settings(PAYMENT_USES_SSL=True, PAYMENT_HOST="example.com")
    def test_failure_url_uses_https_when_ssl_enabled(self) -> None:
        url = self.payment.get_failure_url()
        self.assertTrue(url.startswith("https://"))
        self.assertIn(str(self.payment.pk), url)
        self.assertIn("failure", url)

    @override_settings(PAYMENT_USES_SSL=False, PAYMENT_HOST="example.com")
    def test_failure_url_uses_http_when_ssl_disabled(self) -> None:
        url = self.payment.get_failure_url()
        self.assertTrue(url.startswith("http://"))

    @override_settings(PAYMENT_USES_SSL=True, PAYMENT_HOST="example.com")
    def test_success_url_uses_https_when_ssl_enabled(self) -> None:
        url = self.payment.get_success_url()
        self.assertTrue(url.startswith("https://"))
        self.assertIn(str(self.payment.pk), url)
        self.assertIn("success", url)

    @override_settings(PAYMENT_USES_SSL=False, PAYMENT_HOST="example.com")
    def test_success_url_uses_http_when_ssl_disabled(self) -> None:
        url = self.payment.get_success_url()
        self.assertTrue(url.startswith("http://"))


# ---------------------------------------------------------------------------
# CreatePaymentIntentView
# ---------------------------------------------------------------------------


class CreatePaymentIntentViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.show = make_show(base_ticket_price=20, min_ticket_price=10, max_ticket_price=30)
        self.event = make_event(self.show)
        self.reservation = make_reservation(self.event)

    def _url(self, reservation_id=None) -> str:
        res_id = reservation_id or self.reservation.id
        return f"/payments/{res_id}/intent"

    @patch("stripe.PaymentIntent.create")
    def test_creates_payment_intent(self, mock_create: MagicMock) -> None:
        mock_create.return_value = MagicMock(id="pi_test_123", client_secret="secret_123")

        response = self.client.post(self._url(), {"custom_ticket_price": 20}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertIn("client_secret", response.data)

    @patch("stripe.PaymentIntent.create")
    def test_creates_payment_record(self, mock_create: MagicMock) -> None:
        mock_create.return_value = MagicMock(id="pi_test_123", client_secret="secret_123")

        self.client.post(self._url(), {"custom_ticket_price": 20}, format="json")

        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.first()
        self.assertEqual(payment.custom_ticket_price, 20)
        self.assertEqual(payment.stripe_payment_intent_id, "pi_test_123")

    @patch("stripe.PaymentIntent.create")
    def test_payment_intent_amount_is_total_in_cents(self, mock_create: MagicMock) -> None:
        mock_create.return_value = MagicMock(id="pi_test_123", client_secret="secret_123")

        self.client.post(self._url(), {"custom_ticket_price": 20}, format="json")

        # Should be called with amount in cents (20 EUR = 2000 cents)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["amount"], 2000)
        self.assertEqual(call_kwargs["currency"], "eur")

    @patch("stripe.PaymentIntent.create")
    def test_invalid_price_returns_400(self, mock_create: MagicMock) -> None:
        response = self.client.post(self._url(), {"custom_ticket_price": 5}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
        mock_create.assert_not_called()

    @patch("stripe.PaymentIntent.create")
    def test_missing_price_returns_400(self, mock_create: MagicMock) -> None:
        response = self.client.post(self._url(), {}, format="json")

        self.assertEqual(response.status_code, 400)
        mock_create.assert_not_called()

    def test_nonexistent_reservation_returns_404(self) -> None:
        import uuid

        response = self.client.post(
            f"/payments/{uuid.uuid4()}/intent", {"custom_ticket_price": 20}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    @patch("stripe.PaymentIntent.create")
    def test_metadata_includes_customer_name(self, mock_create: MagicMock) -> None:
        mock_create.return_value = MagicMock(id="pi_test_123", client_secret="secret_123")

        self.client.post(self._url(), {"custom_ticket_price": 20}, format="json")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        expected_name = f"{self.reservation.first_name} {self.reservation.last_name}"
        self.assertEqual(call_kwargs["metadata"]["customer_name"], expected_name)

    @patch("stripe.PaymentIntent.create")
    def test_metadata_includes_reservation_id(self, mock_create: MagicMock) -> None:
        mock_create.return_value = MagicMock(id="pi_test_123", client_secret="secret_123")

        self.client.post(self._url(), {"custom_ticket_price": 20}, format="json")

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["metadata"]["reservation_id"], str(self.reservation.id))


# ---------------------------------------------------------------------------
# Stripe webhook view
# ---------------------------------------------------------------------------


class StripeWebhookViewTest(TestCase):
    URL = "/payments/webhook/stripe"

    def setUp(self) -> None:
        show = make_show()
        event = make_event(show)
        reservation = make_reservation(event)
        self.payment = Payment.objects.create(
            payment_method=Payment.PaymentMethod.CARD,
            reservation=reservation,
            custom_ticket_price=20,
            total=Decimal("20"),
            stripe_payment_intent_id="pi_test_123",
        )

    def _construct_event(self, event_type: str, payment_intent_id: str, **kwargs: Any) -> dict:
        return {
            "type": event_type,
            "data": {"object": {"id": payment_intent_id, **kwargs}},
        }

    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_succeeded_marks_completed(self, mock_construct: MagicMock) -> None:
        mock_construct.return_value = self._construct_event(
            "payment_intent.succeeded", "pi_test_123"
        )

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)

    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_payment_failed_marks_failed(self, mock_construct: MagicMock) -> None:
        mock_construct.return_value = self._construct_event(
            "payment_intent.payment_failed", "pi_test_123"
        )

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)

    @patch("stripe.Webhook.construct_event")
    def test_payment_intent_canceled_marks_failed(self, mock_construct: MagicMock) -> None:
        mock_construct.return_value = self._construct_event(
            "payment_intent.canceled", "pi_test_123"
        )

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.FAILED)

    @patch("reservations.emails.send_refund_mail")
    @patch("stripe.Webhook.construct_event")
    def test_charge_refunded_marks_refunded(
        self, mock_construct: MagicMock, mock_send_refund: MagicMock
    ) -> None:
        mock_construct.return_value = {
            "type": "charge.refunded",
            "data": {"object": {"payment_intent": "pi_test_123"}},
        }

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.REFUNDED)
        mock_send_refund.assert_called_once_with(self.payment.reservation)

    @patch("stripe.Webhook.construct_event")
    def test_unknown_payment_intent_returns_404(self, mock_construct: MagicMock) -> None:
        mock_construct.return_value = self._construct_event(
            "payment_intent.succeeded", "pi_unknown"
        )

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 404)

    @patch("stripe.Webhook.construct_event")
    def test_invalid_signature_returns_401(self, mock_construct: MagicMock) -> None:
        import stripe

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig"
        )

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )

        self.assertEqual(response.status_code, 401)

    @patch("stripe.Webhook.construct_event")
    def test_invalid_payload_returns_400(self, mock_construct: MagicMock) -> None:
        mock_construct.side_effect = ValueError("Invalid payload")

        response = self.client.post(
            self.URL,
            data=_json.dumps({}),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# Stripe return view
# ---------------------------------------------------------------------------


@override_settings(FRONTEND_URL="http://testfrontend.com")
class StripeReturnViewTest(TestCase):
    URL = "/payments/return/stripe"

    def setUp(self) -> None:
        self.show = make_show()
        self.event = make_event(self.show)
        self.reservation = make_reservation(self.event)
        self.payment = Payment.objects.create(
            payment_method=Payment.PaymentMethod.CARD,
            reservation=self.reservation,
            custom_ticket_price=20,
            total=Decimal("20"),
            stripe_payment_intent_id="pi_test_123",
        )

    @patch("stripe.PaymentIntent.retrieve")
    def test_successful_payment_redirects_to_success(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = MagicMock(status="succeeded")

        response = self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("payment/success", response.url)
        self.assertIn(str(self.reservation.id), response.url)

    @patch("stripe.PaymentIntent.retrieve")
    def test_failed_payment_redirects_to_failure(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = MagicMock(status="failed")

        response = self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("payment/failure", response.url)

    @patch("stripe.PaymentIntent.retrieve")
    def test_updates_payment_method_card(self, mock_retrieve: MagicMock) -> None:
        mock_charge = MagicMock()
        mock_charge.payment_method_details = MagicMock(type="card", card=MagicMock(wallet=None))
        mock_retrieve.return_value = MagicMock(
            status="succeeded", get=lambda key: mock_charge if key == "latest_charge" else None
        )

        self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, Payment.PaymentMethod.CARD)

    @patch("stripe.PaymentIntent.retrieve")
    def test_updates_payment_method_apple_pay(self, mock_retrieve: MagicMock) -> None:
        mock_charge = MagicMock()
        mock_charge.payment_method_details = MagicMock(
            type="card", card=MagicMock(wallet=MagicMock(type="apple_pay"))
        )
        mock_retrieve.return_value = MagicMock(
            status="succeeded", get=lambda key: mock_charge if key == "latest_charge" else None
        )

        self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, Payment.PaymentMethod.APPLE)

    @patch("stripe.PaymentIntent.retrieve")
    def test_updates_payment_method_google_pay(self, mock_retrieve: MagicMock) -> None:
        mock_charge = MagicMock()
        mock_charge.payment_method_details = MagicMock(
            type="card", card=MagicMock(wallet=MagicMock(type="google_pay"))
        )
        mock_retrieve.return_value = MagicMock(
            status="succeeded", get=lambda key: mock_charge if key == "latest_charge" else None
        )

        self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, Payment.PaymentMethod.GOOGLE)

    @patch("stripe.PaymentIntent.retrieve")
    def test_updates_payment_method_paypal(self, mock_retrieve: MagicMock) -> None:
        mock_charge = MagicMock()
        mock_charge.payment_method_details = MagicMock(type="paypal")
        mock_retrieve.return_value = MagicMock(
            status="succeeded", get=lambda key: mock_charge if key == "latest_charge" else None
        )

        self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.payment_method, Payment.PaymentMethod.PAYPAL)

    def test_missing_payment_intent_redirects_to_failure(self) -> None:
        response = self.client.get(self.URL, {"reservationId": str(self.reservation.id)})

        self.assertEqual(response.status_code, 302)
        self.assertIn("payment/failure", response.url)

    def test_missing_reservation_id_redirects_to_failure(self) -> None:
        response = self.client.get(self.URL, {"payment_intent": "pi_test_123"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("payment/failure", response.url)

    @patch("stripe.PaymentIntent.retrieve")
    def test_stripe_error_redirects_to_failure(self, mock_retrieve: MagicMock) -> None:
        import stripe

        mock_retrieve.side_effect = stripe.error.StripeError("Error")

        response = self.client.get(
            self.URL, {"payment_intent": "pi_test_123", "reservationId": str(self.reservation.id)}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("payment/failure", response.url)
