from django.db import migrations
from wagtail.models import (
    BootstrapLocaleField,
    BootstrapTranslatableModel,
    BootstrapTranslationKeyField,
)


class Migration(migrations.Migration):
    dependencies = [
        ("basepage", "0001_initial"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [
        BootstrapLocaleField("basepage.Page"),
        BootstrapTranslationKeyField("basepage.Page"),
        BootstrapTranslatableModel("basepage.Page"),
    ]
