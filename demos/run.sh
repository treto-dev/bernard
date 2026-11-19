#!/bin/sh
# Runs a demo end to end without asking: halfway state, bern, migrate, check.
#   demos/run.sh django-user
set -eu
cd "$(dirname "$0")/$1"
./prepare.sh
uv run bern apply --yes
uv run python manage.py migrate -v0
uv run python manage.py shell -v0 -c "$(cat check.py)"
