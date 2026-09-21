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

Beans import as verified only when the source reports them **in stock**
(unknown-stock beans are also kept live). Out-of-stock beans drop off the
public catalog automatically; nothing needs manual admin work for stock
changes. (If you want to curate an out-of-stock bean back onto the site,
verify it manually in the admin.)

## Refreshing the catalog

Scrape every source and re-import in one shot:

    .venv/bin/python manage.py sync_catalog

It runs `scraper/scrape.py`, then imports the resulting `scraper/catalog.jsonl`.
Listings that vanish from a still-active seller's site are marked out-of-stock
(a seller that returned zero records is assumed to be transiently down and is
left untouched). For a daily automated refresh, add a crontab entry:

    crontab -e
    # 17 4 * * * /Users/mammad/git/meta-coffee/scripts/refresh.sh >> /Users/mammad/git/meta-coffee/scripts/refresh.log 2>&1

(Adjust the path for your checkout. The `17 4` run time sits off the top of
the hour to be polite to source sites.)

## Production deployment

### 1. Prepare the server

```bash
# Clone the repo on the target server
git clone https://github.com/Mohammadhp/meta-coffee.git
cd meta-coffee

# Create .env for production
cp .env.example .env
# Edit .env — set DEBUG=False, a real SECRET_KEY, and your domain:
#   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
#   CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
#   DB_HOST=db
#   DB_PORT=5432
```

### 2. Update Caddyfile

Replace `YOUR_DOMAIN` with your actual domain and uncomment `tls`:

```
yourdomain.com, www.yourdomain.com {
    tls you@example.com
    reverse_proxy web:8000
    ...
}
```

### 3. Start

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py import_catalog  # seed data
docker compose exec web python manage.py createsuperuser
```

### 4. Schedule daily refresh

```bash
# On the server, add a cron job to refresh the catalog daily:
crontab -e
# 17 4 * * * cd /path/to/meta-coffee && docker compose exec -T web python manage.py sync_catalog >> logs/refresh.log 2>&1
```

Caddy handles HTTPS automatically via Let's Encrypt. No manual cert setup needed.

## Data

Source catalog: scraper/catalog.jsonl (19 roasters, ~2300 products).
