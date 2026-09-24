import os

LOGLEVEL = os.getenv("DJANGO_LOGLEVEL", "debug").upper()
LOG_DIR = os.getenv("LOG_DIR", "/var/log/zirkusmond")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(module)s %(process)d %(thread)d %(message)s",
        },
        "file": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "django.log"),
            "maxBytes": 100 * 1024 * 1024,  # 100MB
            "backupCount": 10,
            "formatter": "file",
        },
    },
    "loggers": {
        "": {
            "level": LOGLEVEL,
            "handlers": ["console", "file"],
        },
        "django.db.backends": {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "django.utils.autoreload": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "django.template": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
