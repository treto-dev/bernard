from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pronouns = models.CharField(max_length=30, blank=True, default="")
