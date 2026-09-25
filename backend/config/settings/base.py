import logging.config
import os
from pathlib import Path

import sentry_sdk

from config.settings.logging_config import LOGGING
from config.settings.rest_framework_config import REST_FRAMEWORK  # noqa: F401
from config.settings.tinymce_config import TINYMCE_DEFAULT_CONFIG  # noqa: F401
from config.settings.unfold_config import UNFOLD  # noqa: F401

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # zirkusmond/backend

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

INSTALLED_APPS = [
    # unfold
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    # core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party apps
    "corsheaders",
    "payments",
    "anymail",
    "tinymce",
    "rest_framework",
    # Zirkusmond apps
    "events",
    "shows",
    "reservations",
    "stats",
    "newsletter",
    "rentals",
    "homepage_elements",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # analytics middleware
    "stats.middleware.PageViewMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "monddb"),
        "USER": os.environ.get("DB_USER", "mond"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "password"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates/"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
            ],
            "libraries": {},
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"

PAYMENT_MODEL = "reservations.ReservationPayment"

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get(
    "STRIPE_TEST_SECRET_KEY", ""
)
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET") or os.environ.get(
    "STRIPE_TEST_WEBHOOK_SECRET", ""
)

EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
ANYMAIL = {
    "BREVO_API_KEY": os.environ.get("BREVO_API_KEY", ""),
}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "reservation@zirkusmond.de")

# MAILCHIMP - SOON DEPRECATED
MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", "")
MAILCHIMP_SERVER_PREFIX = os.environ.get("MAILCHIMP_SERVER_PREFIX", "")
MAILCHIMP_AUDIENCE_ID = os.environ.get("MAILCHIMP_AUDIENCE_ID", "")

# Listmonk
LISTMONK_URL = os.environ.get("LISTMONK_URL", "")
LISTMONK_API_USERNAME = os.environ.get("LISTMONK_API_USERNAME", "")
LISTMONK_API_PASSWORD = os.environ.get("LISTMONK_API_PASSWORD", "")
LISTMONK_LIST_ID = int(os.environ.get("LISTMONK_LIST_ID", "1"))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", BASE_DIR / "media")

LOGGING_CONFIG = None
logging.config.dictConfig(LOGGING)


# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat - cleanup abandoned payments every 6 hours
CELERY_BEAT_SCHEDULE = {
    "cleanup-abandoned-payments": {
        "task": "reservations.tasks.cleanup_abandoned_payments",
        "schedule": 86000.0,  # 24 hours
    },
}

# sentry
# Only initialize when a DSN is actually configured (e.g. staging/production) -- in local dev
# this is unset, and initializing anyway registers atexit/shutdown hooks for no benefit, which
# can race with interpreter teardown when the dev server is killed by a signal.
SENTRY_DSN_BACKEND = os.environ.get("SENTRY_DSN_BACKEND", "")
if SENTRY_DSN_BACKEND:
    sentry_sdk.init(
        dsn=SENTRY_DSN_BACKEND,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
    )
