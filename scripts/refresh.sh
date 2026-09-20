#!/usr/bin/env bash
# Meta-Coffee daily catalog refresh.
# Scrapes all sources and re-imports into the database.
# Add to crontab (runs once a day, a few minutes off the hour to avoid
# hammering sources at the top of the hour):
#
#   17 4 * * * /Users/mammad/git/meta-coffee/scripts/refresh.sh >> /Users/mammad/git/meta-coffee/scripts/refresh.log 2>&1
#
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python manage.py sync_catalog
