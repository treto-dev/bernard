"""Bernard (as in bernard-l'ermite, the hermit crab) moves the rows of a swapped-out model
into the model that swaps it in: a new shell, the same crab.

Django skips every migration operation on a swapped-out model (``Options.can_migrate``),
so its tables are free to take. For each swap, Bernard renames the legacy tables to the
new model's names, creates what has no legacy counterpart, adds the columns, indexes and
constraints the new model's creating migration declares, relabels the content types,
and records that migration as applied. No row is copied: foreign keys follow the renamed
tables, and everything keyed on a content type (permissions, admin log, Wagtail pages,
revisions, search index) follows the relabelled one. The whole move runs in one
transaction, so a failure anywhere leaves the database untouched.
"""

from dataclasses import dataclass, field

from django.apps import apps
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import CreateModel
from django.db.migrations.recorder import MigrationRecorder

ADVISORY_LOCK = 0xBE4A4D  # PostgreSQL: one Bernard per database at a time
# ponytail: fixed; make it a flag if a busy table needs longer.
LOCK_TIMEOUT = "10s"


# Operations that may be left out when recording a migration, because they only fill data
# the legacy rows already hold.
SKIPPABLE = {"BootstrapTranslatableModel"}  # Wagtail: translation keys of legacy pages


class Refused(Exception):
    pass


@dataclass(frozen=True)
class Move:
    old: str  # "auth.User"
    new: str  # "accounts.User"
    setting: str  # "AUTH_USER_MODEL"
    migration: tuple  # the new model's creating migration, recorded as applied
    records: tuple  # that migration and the ones it replaces
    drops: tuple  # empty tables a previous `migrate` created for the new model
    renames: tuple  # ((legacy_table, table), ...)
    creates: tuple  # tables with no legacy counterpart
    alters: tuple  # ((table, column, old_type, new_type), ...)
    adds: tuple  # ((table, "column" | "index" | "constraint", name), ...)
    relabels: tuple  # ((old_app, old_model, new_app, new_model), ...)
    rows: int = field(compare=False)
    models: dict = field(compare=False, repr=False)  # table -> historical model


def label(model):
    return model._meta.label


def swaps():
    for model in apps.get_models(include_swapped=True):
        if model._meta.swapped:
            yield model, apps.get_model(model._meta.swapped)


def plan(using="default"):
    """Return (moves, problems), reading only."""
    connection = connections[using]
    problems = [str(m) for m in checks.run_checks() if m.is_serious()]
    if not connection.features.can_rollback_ddl:
        problems.append(
            f"{connection.vendor} cannot roll back schema changes, so a failed move would "
            "leave a half-moved database: Bernard only runs on PostgreSQL and SQLite."
        )
    loader = MigrationLoader(connection, ignore_no_migrations=True)
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    moves = []
    for old, new in swaps():
        try:
            move = _plan_one(old, new, loader, connection, tables)
        except Refused as e:
            problems.append(f"{label(old)} → {label(new)}: {e}")
            continue
        if move:
            moves.append(move)
    moves.sort(key=lambda m: len(loader.graph.forwards_plan(m.migration)))
    pending = {r for m in moves for r in m.records} | loader.applied_migrations.keys()
    for move in moves:
        for key in (r for r in move.records if r in loader.graph.node_map):
            missing = sorted(p.key for p in loader.graph.node_map[key].parents if p.key not in pending)
            if missing:
                problems.append(f"{move.new}: apply {missing} first, {key} depends on them.")
    return moves, problems


def _creating_migration(loader, model):
    app, name = model._meta.app_label, model._meta.model_name
    for key, migration in sorted(loader.graph.nodes.items()):
        if key[0] == app and any(
            isinstance(op, CreateModel) and op.name_lower == name for op in migration.operations
        ):
            return key, migration
    raise Refused(f"no migration of {app} creates {name}: run `makemigrations {app}` first.")


def _creating_chain(loader, model):
    """The migration creating `model`, then those of its app that only shape what it created
    (Wagtail's base page takes three). Bernard records them all."""
    key, migration = _creating_migration(loader, model)
    chain, names = [], set()
    while True:
        grown = names | {op.name_lower for op in migration.operations if isinstance(op, CreateModel)}
        stray = _stray_operation(migration, grown)
        if stray and not chain:
            raise Refused(f"{key} also does `{stray.describe()}`, which Bernard would skip when "
                          "recording it: move that operation to a later migration.")
        if stray:
            break
        chain.append((key, migration))
        names = grown
        children = [c.key for c in loader.graph.node_map[key].children if c.key[0] == key[0]]
        if len(children) != 1 or children[0] in loader.applied_migrations:
            break
        key, migration = children[0], loader.graph.nodes[children[0]]
    return chain, names


def _stray_operation(migration, names):
    for op in migration.operations:
        target = getattr(op, "model_name_lower", None) or getattr(op, "name_lower", None)
        if target not in names and type(op).__name__ not in SKIPPABLE:
            return op
    return None


def _count(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM {connection.ops.quote_name(table)}")
        return cursor.fetchone()[0]


def _auto_throughs(model):
    return [
        f.remote_field.through
        for f in model._meta.local_many_to_many
        if f.remote_field.through._meta.auto_created
    ]


def _plan_one(old, new, loader, connection, tables):
    chain, created_names = _creating_chain(loader, new)
    key, last = chain[0][0], chain[-1][0]
    old_table, new_table = old._meta.db_table, new._meta.db_table
    applied = key in loader.applied_migrations
    if old_table not in tables:
        return None  # fresh database, or already moved
    if applied and new_table not in tables:
        raise Refused(f"{key} is recorded as applied but {new_table} is missing.")

    # What the database holds once the move is recorded: every applied migration, plus the chain.
    nodes = [n for n in loader.applied_migrations if n in loader.graph.nodes]
    state = loader.project_state([*nodes, last], at_end=True).apps
    created = [state.get_model(key[0], name) for name in sorted(created_names)]
    models = {t._meta.db_table: t for m in created for t in [m, *_auto_throughs(m)]}

    drops = ()
    if new_table in tables:
        if not _count(connection, old_table):
            return None  # the legacy table was left behind empty: nothing to move
        drops = _droppable(models, key, loader, connection, tables)

    live = {m._meta.db_table for m in apps.get_models(include_auto_created=True)}
    renames, creates, alters, adds, relabels = [], [], [], [], []
    for model in created:
        is_main = model._meta.model_name == new._meta.model_name
        table = model._meta.db_table
        legacy = old_table if is_main else _swap_prefix(table, old, new)
        if legacy not in tables or (not is_main and legacy in live):
            creates.append(table)
            continue
        relabels.append(
            (old._meta.app_label, old._meta.model_name if is_main else model._meta.model_name,
             model._meta.app_label, model._meta.model_name)
        )
        for hm in [model, *_auto_throughs(model)]:
            hm_legacy = legacy + hm._meta.db_table[len(table):]
            if hm_legacy not in tables:
                creates.append(hm._meta.db_table)
                continue
            renames.append((hm_legacy, hm._meta.db_table))
            adds += _missing(hm, hm_legacy, connection)
        if is_main:
            alters += _type_changes(old, model, connection)

    return Move(
        old=label(old), new=label(new), setting=old._meta.swappable, migration=key,
        records=tuple(r for k, m in chain for r in (k, *m.replaces)), drops=drops, renames=tuple(renames),
        creates=tuple(creates), alters=tuple(alters), adds=tuple(adds),
        relabels=tuple(relabels), rows=_count(connection, old_table), models=models,
    )


def _swap_prefix(table, old, new):
    prefix = new._meta.app_label + "_"
    return old._meta.app_label + "_" + table[len(prefix):] if table.startswith(prefix) else None


def _droppable(models, key, loader, connection, tables):
    """A `migrate` already created the new tables, empty: they can go if nothing built on them."""
    existing = tuple(t for t in models if t in tables)
    if any(_count(connection, t) for t in existing):
        raise Refused(f"both the legacy and the new tables hold rows ({', '.join(existing)}): "
                      "merging them is not supported.")
    later = sorted(c.key for c in loader.graph.node_map[key].children
                   if c.key[0] == key[0] and c.key in loader.applied_migrations)
    if later:
        raise Refused(f"the new tables are empty but {later} already changed them: "
                      f"`migrate {key[0]} {key[1]}` back first.")
    with connection.cursor() as cursor:
        for table in tables - set(existing):
            for name, c in connection.introspection.get_constraints(cursor, table).items():
                if c["foreign_key"] and c["foreign_key"][0] in existing:
                    raise Refused(f"{table}.{name} points at the empty {c['foreign_key'][0]}, "
                                  "dropping it would lose that constraint.")
    return existing


def _missing(model, legacy, connection):
    with connection.cursor() as cursor:
        columns = {c.name for c in connection.introspection.get_table_description(cursor, legacy)}
        names = set(connection.introspection.get_constraints(cursor, legacy))
    expected = {f.column: f for f in model._meta.local_concrete_fields}
    orphans = sorted(columns - set(expected))
    if orphans:
        raise Refused(f"{legacy} has columns {orphans} that {label(model)} lacks: "
                      "their data would be left behind. Add them to the new model.")
    table = model._meta.db_table
    return [
        *[(table, "column", f.name) for c, f in expected.items() if c not in columns],
        *[(table, "index", i.name) for i in model._meta.indexes if i.name not in names],
        *[(table, "constraint", c.name) for c in model._meta.constraints if c.name not in names],
    ]


def _type_changes(old, model, connection):
    changes = []
    for f in model._meta.local_concrete_fields:
        try:
            before = old._meta.get_field(f.name).db_type(connection)
        except FieldDoesNotExist:
            continue
        if before != f.db_type(connection):
            changes.append((model._meta.db_table, f.name, before, f.db_type(connection)))
    return changes


def apply(confirmed, using="default"):
    """Run the confirmed moves in one transaction, after checking the plan still holds."""
    connection = connections[using]
    with connection.schema_editor(atomic=True) as editor:
        _lock(connection)
        moves, problems = plan(using)
        if problems:
            raise Refused("\n".join(problems))
        if moves != confirmed:
            raise Refused("the database changed since the plan was shown: run bern again.")
        for move in moves:
            _apply(move, editor, using)
    if apps.is_installed("django.contrib.contenttypes"):
        from django.contrib.contenttypes.models import ContentType

        ContentType.objects.clear_cache()
    return moves


def _lock(connection):
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [ADVISORY_LOCK])
        if not cursor.fetchone()[0]:
            raise Refused("another bern is running on this database.")


def _apply(move, editor, using):
    connection, models = editor.connection, move.models
    for table in move.drops:
        if connection.vendor == "postgresql":
            editor.execute(f"LOCK TABLE {editor.quote_name(table)} IN ACCESS EXCLUSIVE MODE")
        if _count(connection, table):
            raise Refused(f"{table} received rows while Bernard was running.")
    for table in move.drops:
        editor.execute(editor.sql_delete_table % {"table": editor.quote_name(table)})
    for legacy, table in move.renames:
        editor.alter_db_table(models[table], legacy, table)
        _rename_sequence(editor, models[table], legacy)
    for table in move.creates:
        editor.create_model(models[table])
    for sql in editor.deferred_sql:  # their foreign keys, before an alter recreates them
        editor.execute(sql)
    editor.deferred_sql.clear()
    old = apps.get_model(move.old)
    for table, name, _, _ in move.alters:
        model = models[table]
        before = old._meta.get_field(name).clone()
        before.set_attributes_from_name(name)
        before.model = model
        editor.alter_field(model, before, model._meta.get_field(name))
    for table, kind, name in move.adds:
        model = models[table]
        if kind == "column":
            editor.add_field(model, model._meta.get_field(name))
        elif name not in _constraint_names(connection, table):  # SQLite's table rebuild adds them
            items = model._meta.indexes if kind == "index" else model._meta.constraints
            item = next(i for i in items if i.name == name)
            (editor.add_index if kind == "index" else editor.add_constraint)(model, item)
    for relabel in move.relabels:
        _relabel(using, *relabel)
    recorder = MigrationRecorder(connection)
    applied = recorder.applied_migrations()
    for app, name in move.records:
        if (app, name) not in applied:
            recorder.record_applied(app, name)


def _constraint_names(connection, table):
    with connection.cursor() as cursor:
        return set(connection.introspection.get_constraints(cursor, table))


def _rename_sequence(editor, model, legacy):
    """PostgreSQL keeps `<legacy>_id_seq` on a renamed table: give it the name Django expects."""
    pk = model._meta.pk
    if editor.connection.vendor != "postgresql" or pk.model is not model:
        return
    with editor.connection.cursor() as cursor:
        cursor.execute("SELECT pg_get_serial_sequence(%s, %s)",
                       [editor.quote_name(model._meta.db_table), pk.column])
        sequence = cursor.fetchone()[0]
    if sequence and sequence.rsplit(".", 1)[-1].strip('"') == f"{legacy}_{pk.column}_seq":
        new_name = editor.quote_name(f"{model._meta.db_table}_{pk.column}_seq")
        editor.execute(f"ALTER SEQUENCE {sequence} RENAME TO {new_name}")


def _relabel(using, old_app, old_model, new_app, new_model):
    if not apps.is_installed("django.contrib.contenttypes"):
        return
    from django.contrib.contenttypes.models import ContentType

    types = ContentType.objects.db_manager(using)
    stray = types.filter(app_label=new_app, model=new_model).first()
    if stray:  # created lazily by code that ran on the new settings: it must hold nothing
        _delete_unreferenced(stray, using)
    types.filter(app_label=old_app, model=old_model).update(app_label=new_app, model=new_model)
    if old_model != new_model and apps.is_installed("django.contrib.auth"):
        from django.contrib.auth.models import Permission

        perms = Permission.objects.db_manager(using).filter(
            content_type__app_label=new_app, content_type__model=new_model
        )
        for action in ("add", "change", "delete", "view"):
            perms.filter(codename=f"{action}_{old_model}").update(codename=f"{action}_{new_model}")


def _delete_unreferenced(content_type, using):
    """Delete a content type and its permissions, unless any row points at them."""
    connection = connections[using]
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    perms = []
    if apps.is_installed("django.contrib.auth"):
        from django.contrib.auth.models import Permission

        perms = list(Permission.objects.db_manager(using).filter(content_type=content_type))
    for item in [*perms, content_type]:
        for rel in item._meta.related_objects:
            related = rel.related_model
            if (perms and related is type(perms[0])) or related._meta.db_table not in tables:
                continue  # its own permissions are checked one by one; no table, no rows
            if related._base_manager.db_manager(using).filter(**{rel.field.name: item}).exists():
                raise Refused(f"{content_type} is already used by {label(related)}: "
                              "Bernard cannot tell which rows to keep.")
    for item in [*perms, content_type]:
        item.delete(using=using)
