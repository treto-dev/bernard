"""A sites-conformes project that started on the shipped ContentPage and now swaps in its own.

DEMO_STAGE=before gives the project as it was, which prepare.sh uses to build the database.
"""

import os
from pathlib import Path

BEFORE = os.environ.get("DEMO_STAGE") == "before"

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "demo-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "demo.urls"
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    *([] if BEFORE else ["content"]),
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.typed_table_block",
    "wagtail.contrib.routable_page",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "dsfr",
    "sites_conformes",
    "sites_conformes.customimages",
    "sites_conformes.blog",
    "sites_conformes.core",
    "sites_conformes.events",
    "sites_conformes.menus",
    "sites_conformes.proconnect",
    "wagtailmenus",
    "wagtailmarkdown",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
]
if not BEFORE:
    SF_CONTENTPAGE_MODEL = "content.ContentPage"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtailmenus.context_processors.wagtailmenus",
                "sites_conformes.core.context_processors.skiplinks",
            ]
        },
    }
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000

WAGTAIL_SITE_NAME = "Bernard conforme"
WAGTAILADMIN_BASE_URL = "http://localhost:8000"
WAGTAILADMIN_PATH = "admin/"
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILIMAGES_IMAGE_MODEL = "sites_conformes_customimages.CustomImage"
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [("fr", "Français")]
HOST_URL = "localhost"
HOST_PROTO = "http"
PROCONNECT_ACTIVATED = False
TESTING = False
