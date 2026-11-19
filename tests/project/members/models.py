from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Swapped in, but keeps auth.User's tables: nothing to rename."""

    class Meta:
        db_table = "auth_user"
