from django.conf import settings
from wagtail.fields import RichTextField

# A real project would just import its base page; the demo builds its database with
# DEMO_STAGE=before, when the base page was still wagtailcore.Page.
if getattr(settings, "WAGTAIL_PAGE_MODEL", None):
    from basepage.models import Page
else:
    from wagtail.models import Page


class HomePage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + ["body"]
