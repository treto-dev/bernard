# Demos

Three projects caught halfway through a swap: the settings already point at the new model, the
database still holds everything under the old one. Each `prepare.sh` builds that state
(SQLite, from scratch), then it is your turn.

| Demo | Swap | What `migrate` does on its own |
| --- | --- | --- |
| [`django-user`](django-user) | `auth.User` → `accounts.User` (`AUTH_USER_MODEL`) | fails: `InconsistentMigrationHistory` |
| [`wagtail-page`](wagtail-page) | `wagtailcore.Page` → `basepage.Page` (`WAGTAIL_PAGE_MODEL`, Wagtail 8.1) | fails: `InconsistentMigrationHistory` |
| [`sites-conformes`](sites-conformes) | `sites_conformes_core.ContentPage` → `content.ContentPage` (`SF_CONTENTPAGE_MODEL`, 4.4.0rc1) | passes, creates empty tables, and the site crashes with `Manager isn't available` |

```sh
cd demos/django-user
./prepare.sh                      # halfway state
uv run python manage.py migrate   # see it fail
uv run bern                       # the plan
uv run bern apply                 # type the database name: db.sqlite3
uv run python manage.py migrate
uv run python manage.py runserver # admin / admin
```

`./run.sh <demo>` does all of it without asking, then runs the demo's `check.py`: users keep
their passwords and groups, pages their revisions, tags and permissions, and the new fields work.

Each demo's `DEMO_STAGE=before` switch only exists to build the database the old way. In a real
project you change the settings and the code once, and `bern` takes care of the database.

## Notes

- **Wagtail base page**: the new model is named `Page` (in a `basepage` app) and mixes in
  `DefaultBasePageMixin`. The name keeps every page table's `page_ptr` column and the
  `publish_page`-style permission codenames; the mixin keeps the `seo_title`,
  `search_description` and `show_in_menus` columns every existing page has. Its migrations follow
  [Wagtail's recipe](https://docs.wagtail.org/en/stable/advanced_topics/customization/custom_base_page_models.html)
  (three of them); bern records all three.
- Wagtail 8.1's admin page search fails on a custom base page (`Cannot filter search results with
  field "id"`), with or without bern: a fresh project shows it too.
