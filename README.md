# Bernard

```text
                 .-~~~~-.
              .-'  .--.  '-.
             /   .' __ '.   \
            |   /  (  )  \   |
            |   \   ''   /   |
     o   o   \   '.____.'   /
      \ /     '-.        .-'
   ,-( ^ )-.  __/'~~~~~~'
  (_/ \_/ \_)--'
     /|   |\
```

`bern` swaps a Django swappable model partway through a project. You set `AUTH_USER_MODEL`, `WAGTAIL_PAGE_MODEL`, or any `Meta.swappable` setting, and Bernard moves the existing rows into the new model. It copies nothing.

Run it from your project, next to `manage.py`:

```console
$ uvx bern                # plan: reads only
bern · plan · default (postgresql, shop)

  auth.User → accounts.User   (AUTH_USER_MODEL, 1,204 rows)
    rename   auth_user                   →  accounts_user
    rename   auth_user_groups            →  accounts_user_groups
    rename   auth_user_user_permissions  →  accounts_user_user_permissions
    create   accounts_profile
    alter    accounts_user.id  integer → bigint
    add      column accounts_user.nickname
    relabel  auth.user → accounts.user
    record   accounts.0001_initial as applied

$ uvx bern apply          # asks you to type the database name
$ python manage.py migrate
```

`uvx` runs bern in its own environment, which lacks your project's packages. So bern finds your project's virtualenv (`$VIRTUAL_ENV`, or a `.venv` in the current folder or above) and runs again with its Python. Your project's Django and apps win. Without a virtualenv to find, run `uv run --with bern bern` or install `bern` in the project.

## As a Django app

To make every deploy do the move, add `bern` to your project's dependencies and `"bernard"` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = ["bernard", ...]
```

A plain `python manage.py migrate` then moves what there is to move, prints what it did, and migrates. Once everything has moved it says nothing. If the move is refused, `migrate` stops before it changes anything.

- Only a plain `migrate` moves. `migrate --plan`, `--check`, `--fake`, a named app or migration, and the test runner are left to Django.
- `DISABLE_BERNARD=1` in the environment turns it back into Django's `migrate`.
- `python manage.py bern` and `python manage.py bern apply` are the CLI, run by your project.
- List `"bernard"` before any other app that overrides `migrate`: the first one wins.

Installing the app is the confirmation: `migrate` doesn't ask for the database name.

## What it does

Bernard finds the swaps by itself. It loads your settings with `--settings`, `$DJANGO_SETTINGS_MODULE`, or the module your `manage.py` sets, then lists every model whose `_meta.swapped` is set. For each swap:

1. It finds the migration that creates the new model, followed by the ones in its app that only shape what it created. Wagtail's base page takes three: create, bootstrap, finalize. A database that predates the swap has never recorded them, which is why `migrate` fails with `InconsistentMigrationHistory`. Or `migrate` passes, creates empty tables, and leaves your rows behind.
2. It renames the legacy tables to the new names: the model's own table, its many-to-many tables, and companion models of the same name. Foreign keys pointing at them follow automatically.
3. It creates the tables that have no legacy counterpart. It adds the columns, indexes and constraints those migrations declare and the legacy table lacks. It changes column types that differ, such as `AutoField` to `BigAutoField`.
4. It relabels the content types. Everything keyed on a content type follows: permissions, the admin log, Wagtail pages, revisions, and the search and reference indexes.
5. It records those migrations as applied, so `migrate` carries on from there.

This is safe because Django skips every migration operation on a swapped-out model, so nothing will touch its tables again.

If the new model keeps the legacy table name with `Meta.db_table` (for example `db_table = "auth_user"`), Bern renames nothing. It adopts the tables in place, then relabels the content types and records the migrations.

## Safety

- **Plan first.** `bern` with no command only reads. `apply` asks you to type the database name. In a deploy job with no terminal, it refuses unless you pass `--yes`.
- **All or nothing.** The whole move runs in a single transaction. If any step fails, or the process is killed, the database is left exactly as it was. That only works where DDL can be rolled back, so Bernard refuses MySQL and Oracle.
- **No surprises.** `apply` computes the plan again inside the transaction and stops if it differs from the one you confirmed.
- **Fails fast, doesn't queue.** On PostgreSQL, an advisory lock keeps two runs from overlapping. A 10 s `lock_timeout` makes Bernard give up instead of queueing behind a long transaction and blocking your site.
- **Refuses what it can't do right**:
  - errors from Django's system checks;
  - a creating migration that also does something else, like `RunPython`. Wagtail's `BootstrapTranslatableModel` is the exception: it only fills translation keys the legacy pages already have;
  - legacy columns the new model would drop;
  - tables that both hold rows;
  - content types or permissions already in use under the new label.
- **Idempotent.** Once the move is done, `bern apply --yes` does nothing. You can keep it before `migrate` in your deploy job.

If an earlier `migrate` already created the new tables empty, Bernard drops them before moving the legacy ones in. It only does that while they are still empty and nothing else points at them.

## Demos

[`demos/`](demos) holds three projects caught halfway through a swap: Django's user model, Wagtail 8's base page, and the sites-conformes content page. Each `prepare.sh` builds that state; `demos/run.sh <demo>` takes it all the way through.

## Fun

Each command opens with Bernard scuttling across the terminal, and a successful move ends with the crab changing shells. Both only play in an interactive terminal, never in CI or a pipe. `--no-fun` skips them.

## Deploying

Run it where you run `migrate`, between stopping the old code and starting the new one:

```sh
bern apply --yes && python manage.py migrate
```

With `"bernard"` in `INSTALLED_APPS`, `python manage.py migrate` alone does both.

After the move, the old code would query tables that no longer exist.

## Not covered

- **Wagtail images and documents** (`WAGTAILIMAGES_IMAGE_MODEL`, `WAGTAILDOCS_DOCUMENT_MODEL`) are not Django-swappable. `wagtailimages.Image` stays a live model with its own migrations, so its table can't be taken. They need their rows copied instead.
- Index and constraint names inherited from the legacy tables keep their old names. Django finds them by introspection when it later alters them.

## Who is Bernard?

*Bernard l'ermite* is French for hermit crab: when it outgrows its shell, it moves into a new one but stays the same crab deep inside.
