from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls

urlpatterns = [path(settings.WAGTAILADMIN_PATH, include(wagtailadmin_urls))]
urlpatterns += i18n_patterns(path("", include("sites_conformes.core.urls")), prefix_default_language=False)
