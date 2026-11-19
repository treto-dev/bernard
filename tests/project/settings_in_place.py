"""The swap keeps the legacy tables: members.User sets db_table = "auth_user"."""

from settings_before import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "members"]  # noqa: F405
AUTH_USER_MODEL = "members.User"
