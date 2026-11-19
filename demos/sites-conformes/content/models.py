from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from sites_conformes.core.models import AbstractContentPage
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel


class ContentPage(AbstractContentPage):
    """Swapped in for sites_conformes_core.ContentPage (SF_CONTENTPAGE_MODEL).

    Same names as upstream, so the tags through table moves along with the pages.
    """

    tags = ClusterTaggableManager(through="TagContentPage", blank=True)
    subtitle = models.CharField(max_length=255, blank=True, default="")

    content_panels = AbstractContentPage.content_panels + [FieldPanel("tags"), FieldPanel("subtitle")]


class TagContentPage(TaggedItemBase):
    content_object = ParentalKey(ContentPage, related_name="contentpage_tags")
