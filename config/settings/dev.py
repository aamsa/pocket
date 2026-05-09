"""Development settings: SQLite, debug on, relaxed static storage."""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = True
# Dev: accept any host so you can hit the server from your phone on the LAN.
# (Tightened back down for prod.py.)
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Disable manifest storage in dev so missing built CSS doesn't 500 the page.
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

INTERNAL_IPS = ["127.0.0.1"]
