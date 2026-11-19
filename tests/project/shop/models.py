from django.conf import settings
from django.db import models


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="orders")
    watchers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="watched")
