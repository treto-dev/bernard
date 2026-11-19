#!/bin/sh
# Builds the halfway state: a database migrated and filled on wagtailcore.Page, while the
# settings now say WAGTAIL_PAGE_MODEL = "basepage.Page".
set -eu
cd "$(dirname "$0")"
rm -f db.sqlite3
DEMO_STAGE=before uv run python manage.py migrate -v0
DEMO_STAGE=before uv run python manage.py shell -v0 -c "$(cat seed.py)"
echo "Halfway there: 4 pages on wagtailcore.Page, settings on basepage.Page."
echo "Now try: uv run python manage.py migrate   (fails), then: uv run bern"
