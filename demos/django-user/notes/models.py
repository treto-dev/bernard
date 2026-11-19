from django.conf import settings
from django.db import models


class Note(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="notes")
    text = models.TextField()

    def __str__(self):
        return self.text
