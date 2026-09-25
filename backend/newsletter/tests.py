from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from newsletter.models import NewsletterRegistration
from newsletter.services import register_newsletter_email


class RegisterNewsletterEmailTest(TestCase):
    """Tests for the combined DB + Listmonk service function."""

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_creates_database_registration(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("test@example.com")
        self.assertEqual(NewsletterRegistration.objects.count(), 1)
        self.assertEqual(NewsletterRegistration.objects.first().email, "test@example.com")

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_calls_listmonk_subscription(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("test@example.com")
        mock_listmonk.assert_called_once_with("test@example.com")

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_normalizes_email_before_saving(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("  Test@EXAMPLE.COM  ")
        saved = NewsletterRegistration.objects.first()
        self.assertEqual(saved.email, "test@example.com")

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_passes_normalized_email_to_listmonk(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("  Test@EXAMPLE.COM  ")
        mock_listmonk.assert_called_once_with("test@example.com")

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_multiple_calls_create_multiple_records(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("a@example.com")
        register_newsletter_email("b@example.com")
        self.assertEqual(NewsletterRegistration.objects.count(), 2)

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_idempotent_for_duplicate_email(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        register_newsletter_email("test@example.com")
        register_newsletter_email("test@example.com")
        self.assertEqual(NewsletterRegistration.objects.count(), 1)
        # Listmonk is called both times (it's idempotent on their end)
        self.assertEqual(mock_listmonk.call_count, 2)

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_succeeds_even_if_listmonk_is_not_configured(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = ""  # Not configured
        register_newsletter_email("test@example.com")
        self.assertEqual(NewsletterRegistration.objects.count(), 1)
        mock_listmonk.assert_not_called()

    @patch("newsletter.services.subscribe_to_listmonk")
    @patch("newsletter.services.settings")
    def test_succeeds_even_if_listmonk_call_fails(
        self, mock_settings: MagicMock, mock_listmonk: MagicMock
    ) -> None:
        mock_settings.LISTMONK_URL = "http://listmonk:9000"
        mock_listmonk.side_effect = Exception("Connection error")
        register_newsletter_email("test@example.com")
        # Should still create the DB record
        self.assertEqual(NewsletterRegistration.objects.count(), 1)


NEWSLETTER_URL = "/newsletter/register"


class NewsletterRegistrationAPITest(TestCase):
    """Tests for the POST /newsletter/register DRF endpoint."""

    def setUp(self) -> None:
        self.client = APIClient()

    # -----------------------------------------------------------------------
    # Successful registration — new email
    # -----------------------------------------------------------------------

    def test_new_email_returns_201(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {"email": "user@example.com"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_new_email_returns_success_body(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {"email": "user@example.com"}, format="json")
        self.assertEqual(response.data, {"success": True})

    def test_new_email_creates_database_record(self) -> None:
        self.client.post(NEWSLETTER_URL, {"email": "user@example.com"}, format="json")
        self.assertTrue(
            NewsletterRegistration.objects.filter(email="user@example.com").exists(),
            "Expected a NewsletterRegistration record to be created for the submitted email.",
        )

    def test_registration_accepted_via_form_encoded_body(self) -> None:
        # DRF @api_view also accepts application/x-www-form-urlencoded.
        response = self.client.post(NEWSLETTER_URL, {"email": "form@example.com"})
        self.assertEqual(response.status_code, 201)

    # -----------------------------------------------------------------------
    # Duplicate prevention — existing email
    # -----------------------------------------------------------------------

    def test_existing_email_returns_201(self) -> None:
        # The endpoint should be idempotent: re-submitting an already-registered
        # email must still return 201 rather than a conflict error.
        NewsletterRegistration.objects.create(email="existing@example.com")
        response = self.client.post(
            NEWSLETTER_URL, {"email": "existing@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_existing_email_returns_success_body(self) -> None:
        NewsletterRegistration.objects.create(email="existing@example.com")
        response = self.client.post(
            NEWSLETTER_URL, {"email": "existing@example.com"}, format="json"
        )
        self.assertEqual(response.data, {"success": True})

    def test_existing_email_does_not_create_duplicate_record(self) -> None:
        NewsletterRegistration.objects.create(email="existing@example.com")
        self.client.post(NEWSLETTER_URL, {"email": "existing@example.com"}, format="json")
        count = NewsletterRegistration.objects.filter(email="existing@example.com").count()
        self.assertEqual(
            count,
            1,
            "Expected exactly one record after re-submitting a known email.",
        )

    def test_submitting_same_email_twice_does_not_create_duplicate(self) -> None:
        # Two successive requests from the same user (e.g. double-click) must
        # produce only one database row.
        self.client.post(NEWSLETTER_URL, {"email": "twice@example.com"}, format="json")
        self.client.post(NEWSLETTER_URL, {"email": "twice@example.com"}, format="json")
        count = NewsletterRegistration.objects.filter(email="twice@example.com").count()
        self.assertEqual(count, 1)

    # -----------------------------------------------------------------------
    # Missing / empty email — expected 400
    # -----------------------------------------------------------------------

    def test_missing_email_key_returns_400(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_email_key_returns_error_message(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {}, format="json")
        self.assertEqual(response.data, {"error": "Email is required"})

    def test_empty_string_email_returns_400(self) -> None:
        # An empty string is falsy, so it must be rejected the same way as a
        # missing key.
        response = self.client.post(NEWSLETTER_URL, {"email": ""}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_empty_string_email_returns_error_message(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {"email": ""}, format="json")
        self.assertEqual(response.data, {"error": "Email is required"})

    def test_null_email_returns_400(self) -> None:
        # JSON null deserialises to Python None, which is also falsy.
        response = self.client.post(NEWSLETTER_URL, {"email": None}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_email_does_not_create_database_record(self) -> None:
        self.client.post(NEWSLETTER_URL, {}, format="json")
        self.assertEqual(
            NewsletterRegistration.objects.count(),
            0,
            "No record should be created when the email field is absent.",
        )

    def test_empty_string_email_does_not_create_database_record(self) -> None:
        self.client.post(NEWSLETTER_URL, {"email": ""}, format="json")
        self.assertEqual(NewsletterRegistration.objects.count(), 0)

    # -----------------------------------------------------------------------
    # Email format variations
    # -----------------------------------------------------------------------
    # The view does not perform format validation beyond checking for a truthy
    # value; the tests below document which formats are accepted by the
    # endpoint as-is.

    def test_email_with_subdomain_returns_201(self) -> None:
        response = self.client.post(
            NEWSLETTER_URL, {"email": "user@mail.example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_email_with_plus_addressing_returns_201(self) -> None:
        response = self.client.post(
            NEWSLETTER_URL, {"email": "user+newsletter@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_email_with_numbers_in_local_and_domain_returns_201(self) -> None:
        response = self.client.post(
            NEWSLETTER_URL, {"email": "user123@example456.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_email_with_dots_in_local_part_returns_201(self) -> None:
        response = self.client.post(
            NEWSLETTER_URL, {"email": "first.last@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)

    def test_email_with_hyphens_in_domain_returns_201(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {"email": "user@my-domain.com"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_email_with_country_code_tld_returns_201(self) -> None:
        response = self.client.post(NEWSLETTER_URL, {"email": "user@example.de"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_different_emails_create_separate_records(self) -> None:
        # Confirm the unique constraint is keyed on the full address, so two
        # distinct addresses each produce their own row.
        self.client.post(NEWSLETTER_URL, {"email": "a@example.com"}, format="json")
        self.client.post(NEWSLETTER_URL, {"email": "b@example.com"}, format="json")
        self.assertEqual(NewsletterRegistration.objects.count(), 2)

    # -----------------------------------------------------------------------
    # Disallowed HTTP methods
    # -----------------------------------------------------------------------

    def test_get_request_returns_405(self) -> None:
        response = self.client.get(NEWSLETTER_URL)
        self.assertEqual(response.status_code, 405)

    def test_put_request_returns_405(self) -> None:
        response = self.client.put(NEWSLETTER_URL, {"email": "user@example.com"}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_patch_request_returns_405(self) -> None:
        response = self.client.patch(NEWSLETTER_URL, {"email": "user@example.com"}, format="json")
        self.assertEqual(response.status_code, 405)

    def test_delete_request_returns_405(self) -> None:
        response = self.client.delete(NEWSLETTER_URL)
        self.assertEqual(response.status_code, 405)
