"""The project before the swap: plain auth.User."""

import os

SECRET_KEY = "bernard-tests"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "shop"]
ENGINE = "postgresql" if os.environ.get("BERNARD_TEST_PG") else "sqlite3"
DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{ENGINE}",
        "NAME": os.environ.get("BERNARD_TEST_DB", "db.sqlite3"),
    }
}
