import os

from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
SECRET_KEY = "test-secret-key-for-ci"
PAYMENT_HOST = "localhost:8000"
PAYMENT_USES_SSL = False

# Disable Sentry in tests
os.environ["SENTRY_DSN_BACKEND"] = ""

# Use console email backend in tests (don't send real emails)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery - eager mode for tests (tasks run synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
            },
        },
        "formatters": {
            "console": {
                "format": "%(levelname)s [%(name)s] %(message)s",
            },
        },
        "loggers": {
            "": {"level": "WARNING", "handlers": ["console"]},
            "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "django.template": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "PIL": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
    }
)
