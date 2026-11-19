from django.contrib.auth.models import Group, Permission, User

from notes.models import Note

editors = Group.objects.create(name="editors")
editors.permissions.add(*Permission.objects.filter(codename__endswith="_note"))
admin = User.objects.create_superuser("admin", password="admin")
camille = User.objects.create_user("camille", password="camille", is_staff=True)
camille.groups.add(editors)
Note.objects.create(author=admin, text="The rows stay where they are.")
Note.objects.create(author=camille, text="Only the shell changes.")
