from django.contrib.auth.models import User
from sites_conformes.core.models import ContentPage
from wagtail.models import Page, Site
from wagtail.rich_text import RichText

root = Page.get_first_root_node()
home = root.add_child(instance=ContentPage(
    title="Accueil", slug="accueil",
    body=[("paragraph", RichText("<p>Même bernard-l'ermite, nouvelle coquille.</p>"))],
))
home.tags.add("plage")
home.save_revision().publish()
shells = home.add_child(instance=ContentPage(
    title="Coquillages", slug="coquillages",
    body=[("paragraph", RichText("<p>Il en change à mesure qu'il grandit.</p>"))],
))
shells.tags.add("plage", "coquillage")
shells.save_revision().publish()
Site.objects.filter(is_default_site=True).update(root_page=home)
User.objects.create_superuser("admin", password="admin")
