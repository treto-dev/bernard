"""After the swap, with bern installed as an app: `migrate` does the move."""

from settings_after import *  # noqa: F403

INSTALLED_APPS = ["bernard", *INSTALLED_APPS]  # noqa: F405
