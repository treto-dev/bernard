#!/bin/sh
# Builds the halfway state: a database migrated and filled on sites-conformes' own ContentPage,
# while the settings now say SF_CONTENTPAGE_MODEL = "content.ContentPage".
set -eu
cd "$(dirname "$0")"
rm -f db.sqlite3
DEMO_STAGE=before uv run python manage.py migrate -v0
DEMO_STAGE=before uv run python manage.py shell -v0 -c "$(cat seed.py)"
echo "Halfway there: 2 content pages on sites_conformes_core.ContentPage, settings on content.ContentPage."
echo "Now try: uv run python manage.py migrate   (passes, but the pages stay behind and the"
echo "site crashes: 'Manager isn't available'), then: uv run bern"
