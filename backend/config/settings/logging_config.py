import os

LOGLEVEL = os.getenv("DJANGO_LOGLEVEL", "debug").upper()
LOG_DIR = os.getenv("LOG_DIR", None)

# Build handlers list - always include console, add file only if LOG_DIR is set
handlers_list = ["console"]
handlers_config = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "console",
    },
}

formatters_config = {
    "console": {
        "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(module)s %(process)d %(thread)d %(message)s",
    },
}

# Only enable file logging if LOG_DIR is explicitly set (production)
if LOG_DIR:
    handlers_list.append("file")
    handlers_config["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": os.path.join(LOG_DIR, "django.log"),
        "maxBytes": 100 * 1024 * 1024,  # 100MB
        "backupCount": 10,
        "formatter": "file",
    }
    formatters_config["file"] = {
        "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": formatters_config,
    "handlers": handlers_config,
    "loggers": {
        "": {
            "level": LOGLEVEL,
            "handlers": handlers_list,
        },
        "django.db.backends": {
            "level": "WARNING",
            "handlers": handlers_list,
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
