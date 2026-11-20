"""Settings for the Playwright end-to-end tests (frontend/e2e).

Runs Django on :8100 against a throwaway SQLite DB, sends mail via SMTP to a local
Mailpit container, and uses a fixed webhook secret so the test can sign its own
Stripe webhook events. Uses real Stripe *test-mode* keys from the environment.
"""

import os
import tempfile

from .base import *

DEBUG = True  # needed so runserver serves /media
# config/urls.py mounts debug_toolbar urls when DEBUG is on; register the app (without its
# middleware) so the URLconf imports.
INSTALLED_APPS += ["debug_toolbar"]
SILENCED_SYSTEM_CHECKS = ["debug_toolbar.W001"]
ALLOWED_HOSTS = ["*"]
SECRET_KEY = "e2e-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "e2e.sqlite3",
    }
}
MEDIA_ROOT = os.environ.get("E2E_MEDIA_ROOT", os.path.join(tempfile.gettempdir(), "zm-e2e-media"))

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3100")
CSRF_TRUSTED_ORIGINS = ["http://localhost:8100", "http://localhost:3100"]
PAYMENT_HOST = "localhost:8100"
PAYMENT_USES_SSL = False

# Mail goes to Mailpit (see `make e2e-mailpit`); never to Brevo.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("E2E_SMTP_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("E2E_SMTP_PORT", "1025"))
EMAIL_USE_TLS = False
BREVO_API_KEY = ""
ANYMAIL = {"BREVO_API_KEY": ""}

# Only ever talk to Stripe in test mode. The webhook secret is fixed so the test can
# sign the payment_intent.succeeded event itself (no `stripe listen` needed).
STRIPE_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
if not STRIPE_SECRET_KEY.startswith("sk_test_"):
    raise RuntimeError("E2E settings require STRIPE_TEST_SECRET_KEY to be a Stripe test key")
STRIPE_WEBHOOK_SECRET = "whsec_e2e"

# Tasks (confirmation email) run synchronously inside the webhook request.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
