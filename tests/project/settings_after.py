"""The project after the swap: accounts.User replaces auth.User."""

from settings_before import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "accounts"]  # noqa: F405
AUTH_USER_MODEL = "accounts.User"
