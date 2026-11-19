# Bernard

*Bernard l'ermite* is the French hermit crab: when it outgrows its shell, it moves into a new one and stays the same crab.

`bernard` does that for Django swappable models. You set `AUTH_USER_MODEL`, `WAGTAIL_PAGE_MODEL`, or any `Meta.swappable` setting partway through a project, and Bernard moves the existing rows into the new model. It copies nothing.

```console
$ bernard                 # plan: reads only
bernard · plan · default (postgresql, shop)

  auth.User → accounts.User   (AUTH_USER_MODEL, 1,204 rows)
    rename   auth_user                   →  accounts_user
    rename   auth_user_groups            →  accounts_user_groups
    rename   auth_user_user_permissions  →  accounts_user_user_permissions
    create   accounts_profile
    alter    accounts_user.id  integer → bigint
    add      column accounts_user.nickname
    relabel  auth.user → accounts.user
    record   accounts.0001_initial as applied

$ bernard apply           # asks you to type the database name
$ python manage.py migrate
```

## What it does

Bernard finds the swaps by itself. It loads your settings with `--settings`, `$DJANGO_SETTINGS_MODULE`, or the module your `manage.py` sets, then lists every model whose `_meta.swapped` is set. For each swap:

1. It finds the migration that creates the new model. A database that predates the swap has never recorded that migration, which is why `migrate` fails with `InconsistentMigrationHistory`.
2. It renames the legacy tables to the new names: the model's own table, its many-to-many tables, and companion models of the same name. Foreign keys pointing at them follow automatically.
3. It creates the tables that have no legacy counterpart. It adds the columns, indexes and constraints the migration declares and the legacy table lacks. It changes column types that differ, such as `AutoField` to `BigAutoField`.
4. It relabels the content types. Everything keyed on a content type follows: permissions, the admin log, Wagtail pages, revisions, and the search and reference indexes.
5. It records the migration as applied, so `migrate` carries on from there.

This is safe because Django skips every migration operation on a swapped-out model, so nothing will touch its tables again.

## Safety

- **Plan first.** `bernard` with no command only reads. `apply` asks you to type the database name. In a deploy job with no terminal, it refuses unless you pass `--yes`.
- **All or nothing.** The whole move runs in a single transaction. If any step fails, or the process is killed, the database is left exactly as it was. That only works where DDL can be rolled back, so Bernard refuses MySQL and Oracle.
- **No surprises.** `apply` computes the plan again inside the transaction and stops if it differs from the one you confirmed.
- **Fails fast, doesn't queue.** On PostgreSQL, an advisory lock keeps two runs from overlapping. A 10 s `lock_timeout` makes Bernard give up instead of queueing behind a long transaction and blocking your site.
- **Refuses what it can't do right**:
  - errors from Django's system checks;
  - a creating migration that also does something else, like `RunPython`;
  - legacy columns the new model would drop;
  - tables that both hold rows;
  - content types or permissions already in use under the new label.
- **Idempotent.** Once the move is done, `bernard apply --yes` does nothing. You can keep it before `migrate` in your deploy job.

If an earlier `migrate` already created the new tables empty, Bernard drops them before moving the legacy ones in. It only does that while they are still empty and nothing else points at them.

## Deploying

Run it where you run `migrate`, between stopping the old code and starting the new one:

```sh
bernard apply --yes && python manage.py migrate
```

After the move, the old code would query tables that no longer exist.

## Not covered

- **Wagtail images and documents** (`WAGTAILIMAGES_IMAGE_MODEL`, `WAGTAILDOCS_DOCUMENT_MODEL`) are not Django-swappable. `wagtailimages.Image` stays a live model with its own migrations, so its table can't be taken. They need their rows copied instead.
- Index and constraint names inherited from the legacy tables keep their old names. Django finds them by introspection when it later alters them.
