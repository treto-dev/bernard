"""A Django project that started on auth.User and now swaps in accounts.User.

DEMO_STAGE=before gives the project as it was, which prepare.sh uses to build the database.
"""

import os
from pathlib import Path

BEFORE = os.environ.get("DEMO_STAGE") == "before"

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "demo-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "demo.urls"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "notes",
    *([] if BEFORE else ["accounts"]),
]
if not BEFORE:
    AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
STATIC_URL = "static/"
