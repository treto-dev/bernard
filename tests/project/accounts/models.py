from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["nickname"], name="accounts_user_nickname_idx")]


class Profile(models.Model):
    user = models.OneToOneField(User, models.CASCADE)
