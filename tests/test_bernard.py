"""End to end: a project on auth.User switches AUTH_USER_MODEL to accounts.User mid-project.

Each step runs in its own process, as in real life: settings are read once per process.
SQLite by default; BERNARD_TEST_PG=1 runs the same tests on a throwaway PostgreSQL database.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

PROJECT = Path(__file__).parent / "project"

SEED = """
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from shop.models import Order
staff = Group.objects.create(name="staff")
staff.permissions.add(Permission.objects.get(codename="add_order"))
alice = User.objects.create_user("alice", password="pw")
alice.groups.add(staff)
alice.user_permissions.add(Permission.objects.get(codename="change_user", content_type__app_label="auth"))
bob = User.objects.create_user("bob")
Order.objects.create(user=alice).watchers.add(alice, bob)
print(ContentType.objects.get_for_model(User).pk)
"""

CHECK = """
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from accounts.models import Profile
from shop.models import Order
User = get_user_model()
assert User._meta.label == "accounts.User"
alice = User.objects.get(username="alice")
assert alice.check_password("pw") and alice.nickname == ""
assert [g.name for g in alice.groups.all()] == ["staff"]
assert alice.has_perm("accounts.change_user") and alice.has_perm("shop.add_order")
order = Order.objects.get()
assert order.user == alice
assert sorted(u.username for u in order.watchers.all()) == ["alice", "bob"]
Profile.objects.create(user=alice)
assert User.objects.create_user("carol").pk == 3, "the id sequence carries on"
print(ContentType.objects.get_for_model(User).pk)
"""

FOREIGN_KEYS = """
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT string_agg(conrelid::regclass::text, ',' ORDER BY conname) FROM pg_constraint "
              "WHERE contype = 'f' AND confrelid = 'accounts_user'::regclass")
    tables = c.fetchone()[0]
    c.execute("SELECT DISTINCT data_type FROM information_schema.columns WHERE column_name = 'user_id'")
    print(tables + ":" + ",".join(r[0] for r in c.fetchall()))
"""


@pytest.fixture
def db(tmp_path):
    if not os.environ.get("BERNARD_TEST_PG"):
        yield str(tmp_path / "db.sqlite3")
        return
    name = f"bernard_{uuid.uuid4().hex[:8]}"
    subprocess.run(["createdb", name], check=True)
    yield name
    subprocess.run(["dropdb", name], check=True)


def run(db, settings, *args, check=True, env=()):
    env = {**os.environ, "PYTHONPATH": str(PROJECT), "BERNARD_TEST_DB": db,
           "DJANGO_SETTINGS_MODULE": settings, "PYTHONWARNINGS": "ignore", **dict(env)}
    result = subprocess.run([sys.executable, *args], env=env, cwd=PROJECT,
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and result.returncode:
        raise AssertionError(f"{args} failed:\n{result.stdout}\n{result.stderr}")
    return result


def django(db, settings, *args, **kwargs):
    return run(db, settings, "-m", "django", *args, **kwargs)


def bernard(db, *args, **kwargs):
    return run(db, "settings_after", "-m", "bernard.cli", *args, **kwargs)


def legacy_project(db, settings="settings_before"):
    django(db, settings, "migrate", "--skip-checks")
    return django(db, "settings_before", "shell", "-c", SEED).stdout.split()[-1]


def test_moves_auth_user_to_the_swapped_in_model(db):
    content_type = legacy_project(db)
    stuck = django(db, "settings_after", "migrate", check=False)
    assert "InconsistentMigrationHistory" in stuck.stderr

    plan = bernard(db).stdout
    assert "auth.User → accounts.User   (AUTH_USER_MODEL, 2 rows)" in plan
    assert "rename   auth_user_groups" in plan
    assert "create   accounts_profile" in plan
    assert "add      column accounts_user.nickname" in plan
    assert "add      index accounts_user.accounts_user_nickname_idx" in plan
    if os.environ.get("BERNARD_TEST_PG"):  # SQLite stores both as integer
        assert "alter    accounts_user.id  integer → bigint" in plan

    unconfirmed = bernard(db, "apply", check=False)
    assert unconfirmed.returncode == 1 and "pass --yes" in unconfirmed.stdout
    assert "moved in (2 rows, none copied)" in bernard(db, "apply", "--yes").stdout

    django(db, "settings_after", "migrate")
    assert django(db, "settings_after", "shell", "-c", CHECK).stdout.split()[-1] == content_type
    assert "Nothing to move" in bernard(db, "apply", "--yes").stdout
    if os.environ.get("BERNARD_TEST_PG"):  # foreign keys follow the new id type, once each
        fks = django(db, "settings_after", "shell", "-c", FOREIGN_KEYS).stdout.split()[-1]
        assert fks == "accounts_profile,accounts_user_groups,accounts_user_user_permissions,shop_order,shop_order_watchers:bigint"


def test_a_failure_in_flight_changes_nothing(db):
    legacy_project(db)
    plan = bernard(db).stdout
    crash = (
        "import sys, bernard.core as core, bernard.cli as cli\n"
        "def boom(*args): raise RuntimeError('power cut')\n"
        "core._relabel = boom\n"  # after every rename, before the migration is recorded
        "sys.exit(cli.main(['apply', '--yes']))"
    )
    failed = run(db, "settings_after", "-c", crash, check=False)
    assert failed.returncode and "power cut" in failed.stderr
    assert "Nothing changed" in failed.stderr

    assert bernard(db).stdout == plan
    users = "from django.contrib.auth.models import User; print(User.objects.count())"
    assert django(db, "settings_before", "shell", "-c", users).stdout.split()[-1] == "2"


def test_drops_the_empty_tables_an_earlier_migrate_made(db):
    content_type = legacy_project(db, settings="settings_early")
    plan = bernard(db).stdout
    assert "drop     accounts_user  (empty" in plan
    assert "rename   auth_user " in plan

    bernard(db, "apply", "--yes")
    django(db, "settings_after", "migrate")
    assert django(db, "settings_after", "shell", "-c", CHECK).stdout.split()[-1] == content_type


def test_plan_never_creates_a_database(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    if os.environ.get("BERNARD_TEST_PG"):
        pytest.skip("SQLite only")
    result = bernard(str(missing), check=False)
    assert result.returncode == 1 and "No database at" in result.stdout
    assert not missing.exists()


IN_PLACE = """
from django.contrib.auth import get_user_model
from shop.models import Order
User = get_user_model()
assert User._meta.label == "members.User" and User._meta.db_table == "auth_user"
alice = User.objects.get(username="alice")
assert alice.check_password("pw") and alice.has_perm("members.change_user")
assert Order.objects.get().user == alice
print("ok")
"""


def test_adopts_the_legacy_tables_in_place_when_the_new_model_keeps_their_names(db):
    legacy_project(db)
    run_in_place = lambda *args, **kw: run(db, "settings_in_place", *args, **kw)  # noqa: E731
    plan = run_in_place("-m", "bernard.cli").stdout
    assert "auth.User → members.User" in plan
    assert "rename" not in plan and "drop" not in plan
    assert "relabel  auth.user → members.user" in plan

    run_in_place("-m", "bernard.cli", "apply", "--yes")
    run_in_place("-m", "django", "migrate")
    assert run_in_place("-m", "django", "shell", "-c", IN_PLACE).stdout.split()[-1] == "ok"
    assert "Nothing to move" in run_in_place("-m", "bernard.cli", "apply", "--yes").stdout


def test_as_an_installed_app_a_plain_migrate_moves_first(db):
    content_type = legacy_project(db)
    plan = django(db, "settings_app", "bern", "--no-fun").stdout
    assert "auth.User → accounts.User" in plan

    disabled = django(db, "settings_app", "migrate", check=False, env={"DISABLE_BERNARD": "1"})
    assert "InconsistentMigrationHistory" in disabled.stderr
    untouched = django(db, "settings_app", "migrate", "--plan", check=False)
    assert "InconsistentMigrationHistory" in untouched.stderr
    assert django(db, "settings_app", "bern", "--no-fun").stdout == plan, "neither moved anything"

    migrated = django(db, "settings_app", "migrate").stdout
    assert "moved in (2 rows, none copied)" in migrated and "Applying" not in migrated.split("moved in")[0]
    assert django(db, "settings_app", "shell", "-c", CHECK).stdout.split()[-1] == content_type
    assert "bern" not in django(db, "settings_app", "migrate").stdout, "silent once moved"


def test_as_an_installed_app_migrate_still_builds_a_new_database(db):
    assert "bern" not in django(db, "settings_app", "migrate").stdout
    assert django(db, "settings_app", "test", "--noinput").returncode == 0
