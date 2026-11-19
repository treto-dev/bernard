#!/bin/sh
# Builds the halfway state: a database migrated and filled on auth.User, while the
# settings now say AUTH_USER_MODEL = "accounts.User".
set -eu
cd "$(dirname "$0")"
rm -f db.sqlite3
DEMO_STAGE=before uv run python manage.py migrate -v0
DEMO_STAGE=before uv run python manage.py shell -v0 -c "$(cat seed.py)"
echo "Halfway there: 2 users and 2 notes on auth.User, settings on accounts.User."
echo "Now try: uv run python manage.py migrate   (fails), then: uv run bern"
