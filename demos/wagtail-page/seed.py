from django.contrib.auth.models import User
from wagtail.models import Page, Site

from home.models import HomePage

root = Page.get_first_root_node()
home = root.add_child(
    instance=HomePage(title="Bernard's beach", slug="beach", body="<p>Same crab, new shell.</p>")
)
home.save_revision().publish()
about = home.add_child(
    instance=HomePage(title="About hermit crabs", slug="about", body="<p>They move house as they grow.</p>")
)
about.save_revision().publish()
Site.objects.filter(is_default_site=True).update(root_page=home)
User.objects.create_superuser("admin", password="admin")
