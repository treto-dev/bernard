"""accounts installed before AUTH_USER_MODEL points at it: `migrate` makes empty tables."""

from settings_before import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, "accounts"]  # noqa: F405
SILENCED_SYSTEM_CHECKS = ["fields.E304"]  # both user models claim the same reverse accessors
