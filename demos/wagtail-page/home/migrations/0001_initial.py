import django.db.models.deletion
import swapper
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        swapper.dependency("wagtailcore", "Page"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to=swapper.get_model_name("wagtailcore", "Page"),
                    ),
                ),
                ("body", wagtail.fields.RichTextField(blank=True)),
            ],
            options={"abstract": False},
            bases=(swapper.get_model_name("wagtailcore", "Page"),),
        ),
    ]
