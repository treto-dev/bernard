"""After `bern apply` and `migrate`: pages, revisions and page permissions moved to basepage.Page."""

import swapper
from django.test import Client
from django.urls import reverse
from wagtail.models import GroupPagePermission

from home.models import HomePage

Page = swapper.load_model("wagtailcore", "Page")
assert Page._meta.label == "basepage.Page"
assert type(Page.objects.get(depth=1).specific) is Page  # the root, once a wagtailcore.Page
home = HomePage.objects.get(slug="beach")
client = Client()
response = client.get("/")
assert response.status_code == 200 and b"About hermit crabs" in response.content
assert client.get("/about/").status_code == 200
client.login(username="admin", password="admin")
for url in ["/admin/", f"/admin/pages/{home.pk}/", f"/admin/pages/{home.pk}/edit/",
            f"/admin/pages/{home.pk}/history/", reverse("wagtailusers_groups:edit", args=[1])]:
    assert client.get(url).status_code == 200, url
assert {p.permission.content_type.app_label for p in GroupPagePermission.objects.all()} == {"basepage"}
home.review_date = "2027-01-01"  # the field the new base page adds
home.save_revision().publish()
assert HomePage.objects.get(pk=home.pk).review_date.year == 2027
print(f"ok: {Page.objects.count()} pages on {Page._meta.label}, site, admin and revisions intact")
