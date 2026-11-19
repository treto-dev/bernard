"""After `bern apply` and `migrate`: content pages, tags and revisions moved to content.ContentPage."""

import swapper
from django.test import Client
from wagtail.models import Page

ContentPage = swapper.load_model("sites_conformes_core", "ContentPage")
assert ContentPage._meta.label == "content.ContentPage"
shells = ContentPage.objects.get(slug="coquillages")
assert type(Page.objects.get(pk=shells.pk).specific) is ContentPage
assert sorted(t.name for t in shells.tags.all()) == ["coquillage", "plage"]
client = Client()
home = client.get("/")
assert home.status_code == 200 and "nouvelle coquille" in home.content.decode()
assert client.get("/coquillages/").status_code == 200
client.login(username="admin", password="admin")
for url in ["/admin/", f"/admin/pages/{shells.pk}/edit/", f"/admin/pages/{shells.pk}/history/"]:
    assert client.get(url).status_code == 200, url
shells.subtitle = "Le champ que la nouvelle coquille ajoute"
shells.save_revision().publish()
assert ContentPage.objects.get(pk=shells.pk).subtitle.startswith("Le champ")
print(f"ok: {ContentPage.objects.count()} pages on {ContentPage._meta.label}, tags, site and admin intact")
