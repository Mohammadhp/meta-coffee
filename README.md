# Meta-Coffee

Vertical search & discovery for coffee in Iran. Django + PostgreSQL. Not a marketplace —
every result links out to the seller.

## Quickstart

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    cp .env.example .env
    docker compose up -d
    .venv/bin/python manage.py migrate
    .venv/bin/python manage.py import_catalog      # seed from scraper/catalog.jsonl
    .venv/bin/python manage.py createsuperuser
    .venv/bin/python manage.py runserver

## Tests

    .venv/bin/python manage.py test

## Curation

Beans import as unverified drafts. In the Django admin, use "Mark selected as verified"
to publish them (sets `is_verified=True` + `last_verified`). Gear is scraped/live.

## Data

Source catalog: scraper/catalog.jsonl (19 roasters, 2157 products, 474 beans, 1683 gear).
