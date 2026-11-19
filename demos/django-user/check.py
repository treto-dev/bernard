"""After `bern apply` and `migrate`: the users kept their passwords, groups and notes."""

from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()
assert User._meta.label == "accounts.User"
client = Client()
assert client.login(username="camille", password="camille")
notes = client.get("/admin/notes/note/")
assert notes.status_code == 200 and b"Only the shell changes." in notes.content
assert client.get("/admin/accounts/user/").status_code == 403  # camille may only edit notes
client.login(username="admin", password="admin")
assert b"camille" in client.get("/admin/accounts/user/").content
print(f"ok: {User.objects.count()} users on {User._meta.label}, admin and permissions intact")
