from django.db import models
from wagtail.models import AbstractPage, DefaultBasePageMixin


class Page(DefaultBasePageMixin, AbstractPage):
    """The project's own base page.

    Named Page so that page tables keep their `page_ptr` column and the page permissions
    keep their codenames (`publish_page`...). DefaultBasePageMixin keeps the fields every
    existing page has (seo_title, search_description, show_in_menus).
    """

    review_date = models.DateField(blank=True, null=True)

    promote_panels = AbstractPage.promote_panels + ["review_date"]
