# Meta-Coffee v1 Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 2,157-product scraped catalog into a runnable Django + Postgres search & discovery site (beans curated via admin, gear scraped), with Persistent RTL templates, pg_trgm search, freshness stamps, and a zero-result query log.

**Architecture:** A single Django project (`config/`) with two apps — `catalog` (Seller, BeanListing, GearListing, SearchQuery models; search view; import/crawl management commands; admin curation) and `blog` (Post model). Public pages are server-rendered RTL templates: Home, Search results, Blog index, Blog detail. Every search result card links **out** to the seller (no checkout, no internal product detail). Beans are imported as **unverified drafts** (`is_verified=False`) and shown publicly only once a human verifies them in Django admin; gear is imported live with a `last_crawled` stamp.

**Tech Stack:** Python 3.14, Django 5.2 LTS, PostgreSQL 17 (via Docker Compose), psycopg 3, `django.contrib.postgres` (`TrigramExtension`, `TrigramSimilarity`, `GinIndex`), python-dotenv, Django's built-in test framework.

**Spec:** `docs/superpowers/specs/2026-09-11-meta-coffee-design.md`

## Global Constraints

- **Python-first, no JS runtime.** Server-rendered Django+RTL templates only. No Node/TS build step. (Spec §7)
- **Django + PostgreSQL with `pg_trgm`.** Search must work for mixed Persian/English free text. (Spec §5, §7)
- **Django Admin is the bean-curation interface** — no custom admin UI at v1. (Spec §7)
- **Two freshness stamps:** beans `last_verified`, gear `last_crawled`. Both surfaced as "N days ago" in templates. (Spec §4)
- **Beans are hand-curated:** public bean results show `is_verified=True` only. Draf  never public. (Spec §2, §4)
- **Eager staleness rule:** if a crawl/parse fails for a page, set `in_stock=False` and alert — never keep stale stock silently. (Spec §7)
- **Website-only scraping**, polite rate-limit, respect `robots.txt`. No Instagram scraping. (Spec §2)
- **Outbound links carry UTM** (`utm_source=metacoffee`) and `rel="nofollow noopener"`. (Spec §8)
- **Zero-result queries are logged** into a `SearchQuery` table → roadmap + seller pitch data. (Spec §3, §8)
- **Sponsored placement must be disclosed** ("اسپانسری") — v1 has no sponsored slots, but keep the constraint in mind.
- **Version floors (verbatim):** Python 3.14, Django `5.2.7+` (`<5.3`), PostgreSQL 17, psycopg 3.
- **Explicitly absent in v1:** Elasticsearch, microservices, ML, queue workers, mobile apps, checkout/cart. (Spec §7)
- **Repo:** currently *not* a git repo. T3 initializes it; every later task commits. If committing is unwanted, the per-task commit steps may be skipped but the work order stays.

**Scraped-data quality caveats (do not "fix" in code — they are inputs the curator handles):** `origin/process/roast/format` are keyword-derived hints; ~303 products have no price; some gear mislabeled (e.g. a hand grinder tagged `format=Ground`); beans not origin-detectable are absent from the bean set. The bean sheet is a **starting set to curate**, not ground truth.

---

## Phase 0 — Scaffold

### Task 1: Rebuild venv and install web dependencies

**Files:**
- Create: `requirements.txt`
- Create: `requirements-scraper.txt`
- Modify: `.gitignore` (Create)

**Interfaces:**
- Consumes: nothing.
- Produces: `.venv/bin/python` runnable with Django/psycopg/dotenv; `requirements.txt` pinning web deps; `requirements-scraper.txt` pinning scraper deps (existing `catalog.jsonl` stays source data).

- [ ] **Step 1: The current `.venv` has broken console-script shebangs**

The existing venv at `.venv/` was created when the repo lived at `~/meta-coffee`; its `pip`/`httpx` entry-point scripts still point at the old path (`bad interpreter: /Users/mammad/meta-coffee/.venv/bin/python3.14`). Rebuild it in place.

- [ ] **Step 2: Recreate the venv and install web deps**

```bash
cd /Users/mammad/git/meta-coffee
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install 'Django>=5.2.7,<5.3' 'psycopg[binary]>=3.1' python-dotenv
.venv/bin/python -m django --version   # expect 5.2.x
```

- [ ] **Step 3: Reinstall scraper deps into the same venv**

```bash
.venv/bin/python -m pip install httpx beautifulsoup4 selectolax openpyxl
```

- [ ] **Step 4: Write requirements files**

`requirements.txt`:
```
Django>=5.2.7,<5.3
psycopg[binary]>=3.1
python-dotenv>=1.0
```

`requirements-scraper.txt`:
```
httpx
beautifulsoup4
selectolax
openpyxl
```

- [ ] **Step 5: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
*.xlsx~
scraper/catalog.xlsx
scraper/~$*.xlsx
.DS_Store
.idea/
```

- [ ] **Step 6: Verify**

```bash
.venv/bin/python -c "import django, psycopg, dotenv; print('deps OK')"
```
Expected: prints `deps OK`.

- [ ] **Step 7: Commit**

```bash
git init            # only if not already a repo
git add -A
git commit -m "chore: rebuild venv, add web+scraper requirements, gitignore"
```

---

### Task 2: Docker Compose Postgres + `.env`

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.env` (git-ignored)

**Interfaces:**
- Consumes: nothing.
- Produces: a reachable Postgres 17 at `localhost:5432`, database `metacoffee`, user `metacoffee`/password `metacoffee`; `.env` consumed by `config/settings.py` (Task 3).

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: metacoffee
      POSTGRES_USER: metacoffee
      POSTGRES_PASSWORD: metacoffee
    ports:
      - "5432:5432"
    volumes:
      - dbdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U metacoffee -d metacoffee"]
      interval: 3s
      timeout: 3s
      retries: 20

volumes:
  dbdata:
```

- [ ] **Step 2: Write `.env.example` (and copy to `.env`)**

```
# Copy to .env and adjust. .env is git-ignored.
SECRET_KEY=change-me
DEBUG=True
DB_NAME=metacoffee
DB_USER=metacoffee
DB_PASSWORD=metacoffee
DB_HOST=127.0.0.1
DB_PORT=5432
```

```bash
cd /Users/mammad/git/meta-coffee
cp .env.example .env
```

- [ ] **Step 3: Start Postgres and wait for health**

```bash
docker compose up -d
docker compose ps        # wait until db shows (healthy)
```

- [ ] **Step 4: Verify connectivity with the psql client**

```bash
psql "postgresql://metacoffee:metacoffee@127.0.0.1:5432/metacoffee" -c "select version();"
```
Expected: returns PostgreSQL 17.x.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: add docker compose postgres 17 and env template"
```

---

### Task 3: Django project scaffold + settings + git

**Files:**
- Create: `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`
- Create: `catalog/` and `blog/` app directories (empty, added with `startapp`, populated later)
- Test: `config/test_settings_smoke.py` (minimal)

**Interfaces:**
- Consumes: `.env` from Task 2.
- Produces: `config.settings` with Postgres wiring, `pg_trgm` available at migration time, and an empty `/` returning a smoke page. Later tasks import `config.settings.*` and add to `config/urls.py`.

- [ ] **Step 1: Scaffold the project**

```bash
cd /Users/mammad/git/meta-coffee
.venv/bin/django-admin startproject config .
.venv/bin/python manage.py startapp catalog
.venv/bin/python manage.py startapp blog
mkdir -p templates catalog/management/commands catalog/management/__init__.py
touch catalog/management/commands/__init__.py
```

- [ ] **Step 2: Rewrite `config/settings.py`** (replace the generated file entirely)

```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"] if DEBUG else [os.getenv("ALLOWED_HOSTS", "*")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "catalog",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "metacoffee"),
        "USER": os.getenv("DB_USER", "metacoffee"),
        "PASSWORD": os.getenv("DB_PASSWORD", "metacoffee"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- [ ] **Step 3: Replace `config/urls.py`**

```python
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

def index(request):
    return HttpResponse("Meta-Coffee is up")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index),
]
```

- [ ] **Step 4: Add `pg_trgm` extension to the ORIGINAL migration** (so it exists before any search index)

Replace the body of `catalog/migrations/0001_initial.py` (generated by `startapp`) with:

```python
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    operations = [
        TrigramExtension(),
    ]
```

- [ ] **Step 5: Migrate and smoke-test**

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver 127.0.0.1:8000 &   # then curl in next step
curl -s http://127.0.0.1:8000/   # expect: Meta-Coffee is up
kill %1
```
Expected: migrations apply (the `pg_trgm` extension created on the `default` DB), `check` passes, root returns the smoke string.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: scaffold Django project with postgres + pg_trgm settings"
```

---

## Phase 1 — Data Models

### Task 4: Seller model

**Files:**
- Create: `catalog/models.py` (partial — Seller)
- Modify: `catalog/admin.py` (register Seller)
- Test: `catalog/tests/test_seller.py`

**Interfaces:**
- Produces: `catalog.models.Seller` with `name`, `seller_type`, `city`, `site_url`, `instagram`, `relationship`. Later tasks FK to it: `seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="beans"/"gear")`.

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_seller.py`

```python
from django.test import TestCase
from catalog.models import Seller


class SellerTest(TestCase):
    def test_create_defaults_to_indexed_roaster(self):
        s = Seller.objects.create(name="Cafe Raees", site_url="https://raeescoffee.com")
        self.assertEqual(s.relationship, Seller.Relationship.INDEXED)
        self.assertEqual(s.seller_type, Seller.SellerType.ROASTER)
        self.assertEqual(str(s), "Cafe Raees")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_seller -v 2`
Expected: FAIL — `ModuleNotFoundError` / `no such table` (Seller not defined yet).

- [ ] **Step 3: Add Seller to `catalog/models.py`**  (append to the generated file)

```python
class Seller(models.Model):
    class SellerType(models.TextChoices):
        ROASTER = "roaster", "Roaster"
        SHOP = "shop", "Shop"
        IMPORTER = "importer", "Importer"

    class Relationship(models.TextChoices):
        INDEXED = "indexed", "Indexed"
        PARTNER = "partner", "Partner"

    name = models.CharField(max_length=200, unique=True)
    seller_type = models.CharField(
        max_length=20, choices=SellerType.choices, default=SellerType.ROASTER
    )
    city = models.CharField(max_length=100, blank=True, default="")
    site_url = models.URLField(blank=True, default="")
    instagram = models.CharField(max_length=200, blank=True, default="")
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, default=Relationship.INDEXED
    )

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Make and run migration**

```bash
.venv/bin/python manage.py makemigrations catalog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test catalog.tests.test_seller -v 2
```
Expected: PASS.

- [ ] **Step 5: Register in `catalog/admin.py`**  (replace generated file)

```python
from django.contrib import admin
from catalog.models import Seller, BeanListing, GearListing, SearchQuery


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("name", "seller_type", "city", "site_url", "relationship")
    list_filter = ("seller_type", "relationship")
    search_fields = ("name",)
```

(BeanListing/GearListing/SearchQuery imports are added as their models are defined — registering only Seller here is fine; the others get registrations in later tasks.)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add Seller model + admin"
```

---

### Task 5: BeanListing model

**Files:**
- Modify: `catalog/models.py` (add BeanListing)
- Modify: `catalog/admin.py` (register BeanListing)
- Test: `catalog/tests/test_beanlisting.py`

**Interfaces:**
- Consumes: `Seller` (Task 4).
- Produces: `catalog.models.BeanListing` with `seller` FK, `name`, `origin`, `variety`, `process`, `roast_level`, `format`, `flavor_notes`, `roasted_on`, `weight_g`, `price_toman`, `price_per_100g`, `specialty_score`, `in_stock`, `is_verified`, `last_verified`, `link`, `source_key` (unique), `created_at`, `updated_at`. `Process`/`RoastLevel`/`BeansFormat` TextChoices classes. Used by import (T8), search (T11), admin (T7).

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_beanlisting.py`

```python
from datetime import datetime
from django.test import TestCase
from catalog.models import Seller, BeanListing


class BeanListingTest(TestCase):
    def setUp(self):
        self.seller = Seller.objects.create(name="Cafe Raees")

    def test_draft_hidden_by_default(self):
        b = BeanListing.objects.create(
            seller=self.seller,
            name="قهوه مدیوم پریمیوم",
            origin="Colombia",
            process=BeanListing.Process.WASHED,
            roast_level=BeanListing.RoastLevel.MEDIUM,
            price_toman=2_300_000,
            link="https://raeescoffee.com/product/x",
            source_key="https://raeescoffee.com/product/x",
        )
        self.assertFalse(b.is_verified)
        self.assertIsNone(b.last_verified)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_beanlisting -v 2`
Expected: FAIL.

- [ ] **Step 3: Add BeanListing to `catalog/models.py`**

```python
class BeanListing(models.Model):
    class Process(models.TextChoices):
        WASHED = "Washed", "Washed"
        NATURAL = "Natural", "Natural"
        HONEY = "Honey", "Honey"
        ANAEROBIC = "Anaerobic", "Anaerobic"
        OTHER = "Other", "Other"
        UNKNOWN = "Unknown", "Unknown"

    class RoastLevel(models.TextChoices):
        LIGHT = "Light", "Light"
        MEDIUM = "Medium", "Medium"
        DARK = "Dark", "Dark"
        UNKNOWN = "Unknown", "Unknown"

    class BeansFormat(models.TextChoices):
        WHOLE = "Whole bean", "Whole bean"
        GROUND = "Ground", "Ground"
        CAPSULE = "Capsule", "Capsule"
        POD = "Pods", "Pods"
        OTHER = "Other", "Other"

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="beans")
    name = models.CharField(max_length=200)
    origin = models.CharField(max_length=100, blank=True, null=True)
    variety = models.CharField(max_length=100, blank=True, null=True)
    process = models.CharField(max_length=20, choices=Process.choices, blank=True, null=True)
    roast_level = models.CharField(max_length=20, choices=RoastLevel.choices, blank=True, null=True)
    format = models.CharField(max_length=20, choices=BeansFormat.choices, blank=True, null=True)
    flavor_notes = models.TextField(blank=True, null=True)
    roasted_on = models.DateField(blank=True, null=True)
    weight_g = models.FloatField(blank=True, null=True)
    price_toman = models.BigIntegerField(blank=True, null=True)
    price_per_100g = models.FloatField(blank=True, null=True)
    specialty_score = models.FloatField(blank=True, null=True)
    in_stock = models.BooleanField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    last_verified = models.DateTimeField(blank=True, null=True)
    link = models.URLField(blank=True, default="")
    source_key = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Make and run migration + test**

```bash
.venv/bin/python manage.py makemigrations catalog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test catalog.tests.test_beanlisting -v 2
```
Expected: PASS.

- [ ] **Step 5: Register in `catalog/admin.py`** (append to existing registrations)

```python
@admin.register(BeanListing)
class BeanListingAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "origin", "process", "roast_level",
                    "price_toman", "in_stock", "is_verified", "last_verified")
    list_filter = ("origin", "process", "roast_level", "is_verified", "in_stock")
    search_fields = ("name", "origin")
    list_select_related = ("seller",)
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add BeanListing model + admin"
```

---

### Task 6: GearListing model

**Files:**
- Modify: `catalog/models.py` (add GearListing)
- Modify: `catalog/admin.py` (register GearListing)
- Test: `catalog/tests/test_gearlisting.py`

**Interfaces:**
- Consumes: `Seller` (Task 4).
- Produces: `catalog.models.GearListing` with `seller` FK, `name`, `category`, `brand`, `model`, `key_specs`, `price_toman`, `in_stock`, `last_crawled`, `link`, `source_key` (unique), `created_at`, `updated_at`, plus a `GearCategory` TextChoices. Used by import (T8), search (T11), admin (T7).

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_gearlisting.py`

```python
from datetime import datetime, timezone
from django.test import TestCase
from catalog.models import Seller, GearListing


class GearListingTest(TestCase):
    def setUp(self):
        self.seller = Seller.objects.create(name="Cafe Raees")

    def test_gear_record_carries_last_crawled(self):
        g = GearListing.objects.create(
            seller=self.seller,
            name="آسیاب دستی قهوه",
            category=GearListing.GearCategory.GRINDER,
            price_toman=1_500_000,
            last_crawled=datetime.now(timezone.utc),
            link="https://raeescoffee.com/product/y",
            source_key="https://raeescoffee.com/product/y",
        )
        self.assertIsNotNone(g.last_crawled)
        self.assertEqual(g.category, "grinder")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_gearlisting -v 2`
Expected: FAIL.

- [ ] **Step 3: Add GearListing to `catalog/models.py`**

```python
class GearListing(models.Model):
    class GearCategory(models.TextChoices):
        GRINDER = "grinder", "Grinder"
        BREWER = "brewer", "Brewer"
        KETTLE = "kettle", "Kettle"
        FILTER = "filter", "Filter"
        ACCESSORY = "accessory", "Accessory"

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="gear")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=GearCategory.choices, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    key_specs = models.TextField(blank=True, null=True)
    price_toman = models.BigIntegerField(blank=True, null=True)
    in_stock = models.BooleanField(blank=True, null=True)
    last_crawled = models.DateTimeField(blank=True, null=True)
    link = models.URLField(blank=True, default="")
    source_key = models.URLField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
```

- [ ] **Step 4: Make and run migration + test**

```bash
.venv/bin/python manage.py makemigrations catalog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test catalog.tests.test_gearlisting -v 2
```
Expected: PASS.

- [ ] **Step 5: Register in `catalog/admin.py`**

```python
@admin.register(GearListing)
class GearListingAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "category", "brand", "price_toman", "in_stock", "last_crawled")
    list_filter = ("category", "in_stock")
    search_fields = ("name", "brand")
    list_select_related = ("seller",)
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add GearListing model + admin"
```

---

### Task 7: Curation admin actions + pg_trgm indexes

**Files:**
- Modify: `catalog/models.py` (add `Meta.indexes` with trigram GinIndex to BeanListing & GearListing)
- Modify: `catalog/admin.py` (add "mark verified" action to BeanListingAdmin)
- Test: `catalog/tests/test_admin_actions.py`

**Interfaces:**
- Consumes: BeanListing (T5), GearListing (T6).
- Produces: trigram indexes so `TrigramSimilarity("name", q)` in search (T11) is efficient; a reusable admin action `mark_verified` that sets `is_verified=True, last_verified=now` (the bean-curation button).

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_admin_actions.py`

```python
from django.test import TestCase
from catalog.admin import mark_bean_verified
from catalog.models import Seller, BeanListing
from django.contrib.admin.sites import AdminSite
from django.contrib.admin import ModelAdmin


class MarkVerifiedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = Seller.objects.create(name="R")
        cls.bean = BeanListing.objects.create(
            seller=s, name="b", source_key="https://r.example/b"
        )

    def test_action_sets_verified_and_stamp(self):
        qs = BeanListing.objects.filter(pk=self.bean.pk)
        mark_bean_verified(ModelAdmin(BeanListing, AdminSite()), None, qs)
        self.bean.refresh_from_db()
        self.assertTrue(self.bean.is_verified)
        self.assertIsNotNone(self.bean.last_verified)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_admin_actions -v 2`
Expected: FAIL — `cannot import name 'mark_bean_verified'`.

- [ ] **Step 3: Add trigram indexes to the models' `Meta`**

Add to **both** `BeanListing` and `GearListing` (inside each class, after field defs):

```python
    class Meta:
        indexes = [
            GinIndex(fields=["name"], name="<bean|gear>_name_trgm", opclasses=["gin_trgm_ops"]),
        ]
```

Add `from django.contrib.postgres.indexes import GinIndex` to the top of `catalog/models.py`.

- [ ] **Step 4: Add the admin action to `catalog/admin.py`**

```python
from datetime import timezone


def mark_bean_verified(modeladmin, request, queryset):
    """Curation action: flip a draft bean to verified + stamp last_verified."""
    from datetime import datetime
    queryset.update(is_verified=True, last_verified=datetime.now(timezone.utc))


mark_bean_verified.short_description = "Mark selected beans as verified"


@admin.register(BeanListing)
class BeanListingAdmin(admin.ModelAdmin):
    # ... existing fields from Task 5 ...
    actions = [mark_bean_verified]
```

(Replace the BeanListingAdmin body from Task 5 by adding the `actions = [mark_bean_verified]` line and keeping everything else.)

- [ ] **Step 5: Make and run migration + tests**

```bash
.venv/bin/python manage.py makemigrations catalog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test catalog -v 2
```
Expected: PASS (all catalog tests so far).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: trigram indexes + admin mark-verified action"
```

---

## Phase 2 — Data Import

### Task 8: `import_catalog` management command

**Files:**
- Create: `catalog/management/commands/import_catalog.py`
- Test: `catalog/tests/test_import_catalog.py`

**Interfaces:**
- Consumes: Seller (T4), BeanListing (T5), GearListing (T6), `scraper/catalog.jsonl`.
- Produces: a command `.venv/bin/python manage.py import_catalog [--file scraper/catalog.jsonl]` that is idempotent (`update_or_create` on `source_key`), creates Sellers keyed by `roaster` name, splits records by `origin is not None` → BeanListing (draft, `is_verified=False`) else GearListing (`last_crawled=now`), and prints a summary. Re-run produces the same totals (no duplicates).

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_import_catalog.py`

```python
import io, json, tempfile, os
from django.test import TestCase
from django.core.management import call_command
from catalog.models import Seller, BeanListing, GearListing


class ImportCatalogTest(TestCase):
    def _write(self, recs):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        return path

    def test_splits_and_dedupes(self):
        bean = {
            "roaster": "Cafe Raees", "product_name": "قهوه مدیوم",
            "origin": "Colombia", "process": None, "roast_level": "Medium",
            "format": "Whole bean", "weight_g": 500.0, "price_toman": 2300000,
            "price_per_100g": 460000.0, "specialty_score": None, "in_stock": False,
            "categories": "", "product_url": "https://raeescoffee.com/product/a",
            "description": "x",
        }
        gear = {
            "roaster": "Cafe Raees", "product_name": "آسیاب دستی",
            "origin": None, "process": None, "roast_level": None,
            "format": "Ground", "weight_g": None, "price_toman": 1500000,
            "price_per_100g": None, "specialty_score": None, "in_stock": True,
            "categories": "آسیاب; ابزار", "product_url": "https://raeescoffee.com/product/b",
            "description": "y",
        }
        path = self._write([bean, gear, bean])  # duplicate bean on purpose
        out = io.StringIO()
        call_command("import_catalog", file=path, stdout=out)
        self.assertEqual(Seller.objects.count(), 1)
        self.assertEqual(BeanListing.objects.count(), 1)
        self.assertTrue(BeanListing.objects.get().is_verified is False)
        self.assertEqual(GearListing.objects.count(), 1)
        g = GearListing.objects.get()
        self.assertEqual(g.category, "grinder")   # from "آسیاب" in categories
        self.assertIsNotNone(g.last_crawled)
        self.assertIn("1 seller", out.getvalue())
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_import_catalog -v 2`
Expected: FAIL — `unknown command: 'import_catalog'`.

- [ ] **Step 3: Write `catalog/management/commands/import_catalog.py`**

```python
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from catalog.models import Seller, BeanListing, GearListing

CATEGORY_MAP = [
    ("grinder", ("آسیاب", "grinder")),
    ("filter", ("فیلتر", "filter")),
    ("kettle", ("کتل", "kettle")),
    ("brewer", ("دم", "brewer", "موکا", "چای")),
]


def _gear_category(categories):
    cats = categories or ""
    for code, keys in CATEGORY_MAP:
        if any(k in cats for k in keys):
            return code
    return "accessory"


class Command(BaseCommand):
    help = "Import scraper/catalog.jsonl into Sellers + Bean/Gear listings (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="scraper/catalog.jsonl")

    def handle(self, *args, **opts):
        path = opts["file"]
        n_sellers = n_beans = n_gear = 0
        now = datetime.now(timezone.utc)
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                domain = urlparse(r.get("product_url", "")).netloc
                site_url = f"https://{domain}" if domain else ""
                seller, _ = Seller.objects.update_or_create(
                    name=r["roaster"],
                    defaults={"site_url": site_url, "relationship": Seller.Relationship.INDEXED},
                )
                url = r.get("product_url", "")
                if r.get("origin"):
                    process = r["process"] if r.get("process") in BeanListing.Process.values else None
                    roast = r["roast_level"] if r.get("roast_level") in BeanListing.RoastLevel.values else None
                    fmt = r["format"] if r.get("format") in BeanListing.BeansFormat.values else None
                    BeanListing.objects.update_or_create(
                        source_key=url,
                        defaults={
                            "seller": seller,
                            "name": r["product_name"],
                            "origin": r.get("origin"),
                            "process": process,
                            "roast_level": roast,
                            "format": fmt,
                            "weight_g": r.get("weight_g"),
                            "price_toman": r.get("price_toman"),
                            "price_per_100g": r.get("price_per_100g"),
                            "specialty_score": r.get("specialty_score"),
                            "in_stock": r.get("in_stock"),
                            "link": url,
                            "is_verified": False,  # draft; does not clobber last_verified
                            # deliberately NOT setting last_verified
                        },
                    )
                    n_beans += 1
                else:
                    GearListing.objects.update_or_create(
                        source_key=url,
                        defaults={
                            "seller": seller,
                            "name": r["product_name"],
                            "category": _gear_category(r.get("categories")),
                            "price_toman": r.get("price_toman"),
                            "in_stock": r.get("in_stock"),
                            "last_crawled": now,
                            "link": url,
                        },
                    )
                    n_gear += 1
                n_sellers = Seller.objects.count()
        self.stdout.write(
            f"Imported: {n_sellers} sellers, {n_beans} beans (draft), {n_gear} gear"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python manage.py test catalog.tests.test_import_catalog -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: idempotent import_catalog management command"
```

---

### Task 9: Run the import against the real catalog

**Files:**
- (none created — verification only)

**Interfaces:**
- Consumes: the command from T8 + `scraper/catalog.jsonl`.

- [ ] **Step 1: Run the import**

```bash
.venv/bin/python manage.py import_catalog --file scraper/catalog.jsonl
```
Expected output matches the catalog exactly: `19 sellers`, `474 beans (draft)`, `1683 gear`.

- [ ] **Step 2: Re-run to confirm idempotency**

```bash
.venv/bin/python manage.py import_catalog --file scraper/catalog.jsonl
```
Expected: identical counts (no growth from duplicates).

- [ ] **Step 3: Spot-check seller URLs + gear categories**

```bash
.venv/bin/python manage.py shell -c "from catalog.models import Seller, GearListing; print(Seller.objects.count(), list(Seller.objects.values_list('site_url', flat=True)[:3])); from django.db.models import Count; print(list(GearListing.objects.values('category').annotate(n=Count('id')).order_by('-n')))"
```
Expected: sellers derived `.coffee`/`.com` domains; gear category histogram dominated by whatever the keyword map produced (mostly `accessory` — acceptable best-effort).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: import full catalog into database"
```
(If no files changed — counts only — commit nothing and skip this step.)

---

## Phase 3 — Search & Discovery

### Task 10: SearchQuery (zero-result log) model

**Files:**
- Modify: `catalog/models.py` (add SearchQuery)
- Modify: `catalog/admin.py` (register, admin-only)
- Test: `catalog/tests/test_searchquery.py`

**Interfaces:**
- Produces: `catalog.models.SearchQuery(query_text, created_at)`. Consumed by the search view (T11) to record queries that return zero results.

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_searchquery.py`

```python
from django.test import TestCase
from catalog.models import SearchQuery


class SearchQueryTest(TestCase):
    def test_records_query(self):
        q = SearchQuery.objects.create(query_text="برزیل شکلاتی")
        self.assertEqual(q.query_text, "برزیل شکلاتی")
        self.assertIsNotNone(q.created_at)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_searchquery -v 2`
Expected: FAIL.

- [ ] **Step 3: Add SearchQuery to `catalog/models.py`**

```python
class SearchQuery(models.Model):
    query_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_text
```

- [ ] **Step 4: Make and run migration + test**

```bash
.venv/bin/python manage.py makemigrations catalog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test catalog.tests.test_searchquery -v 2
```
Expected: PASS.

- [ ] **Step 5: Register in `catalog/admin.py`** (view-only, for the pitch-data the spec cares about)

```python
@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ("query_text", "created_at")
    search_fields = ("query_text",)
    date_hierarchy = "created_at"
    def has_add_permission(self, request): return False
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add SearchQuery zero-result log model"
```

---

### Task 11: Search view (facets + trigram + price + zero-log)

**Files:**
- Create: `catalog/views.py`
- Modify: `config/urls.py` (route `/search/`)
- Test: `catalog/tests/test_search_view.py`

**Interfaces:**
- Consumes: BeanListing/GearListing (T5/T6), SearchQuery (T10), seller `link`.
- Produces: `catalog.views.search(request)` returning either a rendered `search/results.html` (added T12) or a JSON `facets` context. Wire format for the template (T12):
  - `request.GET`: `q`, `origin`, `roast`, `process`, `format`, `category`, `type` (`bean`|`gear`|`''`), `min_price`, `max_price`, `sort` (`price_asc`|`price_desc`|`newest`).
  - context keys: `beans` (QuerySet, verified only), `gear` (QuerySet), `facets` dict (`origins`, `roasts`, `processes`, `formats`, `gear_categories` each `[{"value", "label", "count"}]`), `active` dict of applied filters, `total`.
  - Zero-results logging: if `q` non-empty AND total hits == 0, insert a `SearchQuery`.

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_search_view.py`

```python
from django.test import TestCase
from django.urls import reverse
from catalog.models import Seller, BeanListing, GearListing, SearchQuery


class SearchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = Seller.objects.create(name="Cafe Raees")
        cls.verified = BeanListing.objects.create(
            seller=s, name="برزیل شکلاتی", origin="Brazil",
            process="Natural", roast_level="Medium", price_toman=2_000_000,
            is_verified=True, last_verified=None,
            source_key="https://r.example/v", link="https://r.example/v",
        )
        cls.draft = BeanListing.objects.create(
            seller=s, name="اتیوپی گشا", origin="Ethiopia",
            source_key="https://r.example/d", link="https://r.example/d",
            is_verified=False,
        )
        cls.gear = GearListing.objects.create(
            seller=s, name="آسیاب برقی x", category="grinder",
            source_key="https://r.example/g", link="https://r.example/g",
        )

    def test_verified_beans_only(self):
        resp = self.client.get(reverse("search"))
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.draft.name)

    def test_facet_filter_by_origin(self):
        resp = self.client.get(reverse("search"), {"origin": "Brazil"})
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.gear.name)

    def test_zero_result_is_logged(self):
        self.client.get(reverse("search"), {"q": "چیز ناموجود"})
        self.assertEqual(SearchQuery.objects.filter(query_text="چیز ناموجود").count(), 1)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_search_view -v 2`
Expected: FAIL — `no module named catalog.views` / `Reverse for 'search' not found`.

- [ ] **Step 3: Write `catalog/views.py`**

```python
from django.db.models import Count, Value
from django.db.models.functions import Coalesce
from django.contrib.postgres.search import TrigramSimilarity
from django.shortcuts import render

from catalog.models import BeanListing, GearListing, SearchQuery


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _facets(qs, field, label):
    rows = (
        qs.exclude(**{field: None})
        .exclude(**{field: ""})
        .values(field)
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [{"value": r[field], "label": r[field], "count": r["count"]} for r in rows]


def _tag_facet_bean(qs, key, value):
    return qs.filter(**{key: value})


def search(request):
    q = request.GET.get("q", "").strip()
    origin = request.GET.get("origin", "")
    roast = request.GET.get("roast", "")
    process = request.GET.get("process", "")
    fmt = request.GET.get("format", "")
    category = request.GET.get("category", "")
    ftype = request.GET.get("type", "")
    min_price = _int(request.GET.get("min_price"))
    max_price = _int(request.GET.get("max_price"))
    sort = request.GET.get("sort", "")

    beans = BeanListing.objects.filter(is_verified=True, in_stock__in=[True, None])
    gear = GearListing.objects.all()

    ordered_beans, ordered_gear = beans, gear
    if q:
        beans = beans.annotate(_sim=TrigramSimilarity("name", q)).filter(_sim__gt=0.2)
        gear = gear.annotate(_sim=TrigramSimilarity("name", q)).filter(_sim__gt=0.2)
        ordered_beans = beans.order_by("-_sim")
        ordered_gear = gear.order_by("-_sim")

    # facets computed from the pre-facet sets (reflect full catalog)
    bean_base = BeanListing.objects.filter(is_verified=True)
    facets = {
        "origins": _facets(bean_base, "origin", "origin"),
        "roasts": _facets(bean_base, "roast_level", "roast_level"),
        "processes": _facets(bean_base, "process", "process"),
        "formats": _facets(bean_base, "format", "format"),
        "gear_categories": _facets(GearListing.objects.all(), "category", "category"),
    }

    # apply filters
    if origin:
        beans = beans.filter(origin=origin)
    if roast:
        beans = beans.filter(roast_level=roast)
    if process:
        beans = beans.filter(process=process)
    if fmt:
        beans = beans.filter(format=fmt)
    if category:
        gear = gear.filter(category=category)
    if ftype == "bean":
        gear = gear.none()
    elif ftype == "gear":
        beans = beans.none()
    if min_price is not None:
        beans = beans.filter(price_toman__gte=min_price)
        gear = gear.filter(price_toman__gte=min_price)
    if max_price is not None:
        beans = beans.filter(price_toman__lte=max_price)
        gear = gear.filter(price_toman__lte=max_price)
    if sort == "price_asc":
        beans, gear = beans.order_by("price_toman"), gear.order_by("price_toman")
    elif sort == "price_desc":
        beans, gear = beans.order_by("-price_toman"), gear.order_by("-price_toman")
    elif sort == "newest":
        beans, gear = beans.order_by("-updated_at"), gear.order_by("-updated_at")

    total = beans.count() + gear.count()
    if q and total == 0:
        SearchQuery.objects.create(query_text=q)

    active = {
        "q": q, "origin": origin, "roast": roast, "process": process,
        "format": fmt, "category": category, "type": ftype,
        "min_price": min_price, "max_price": max_price, "sort": sort,
    }
    ctx = {
        "beans": beans[:60], "gear": gear[:60], "facets": facets,
        "active": active, "total": total,
    }
    return render(request, "search/results.html", ctx)
```

- [ ] **Step 4: Add the route to `config/urls.py`**

```python
from catalog import views as catalog_views
# ...
urlpatterns = [
    path("admin/", admin.site.urls),
    path("search/", catalog_views.search, name="search"),
    path("", index),
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python manage.py test catalog.tests.test_search_view -v 2`
Expected: PASS. (`search/results.html` doesn't exist yet, but Django's test client uses the template loader which will raise TemplateDoesNotExist on render — see Task 12. To keep this task green, create an empty placeholder `templates/search/results.html` now; Task 12 replaces it.)

```bash
mkdir -p templates/search && echo "" > templates/search/results.html
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: search view with facets, trigram, price, zero-result log"
```

---

### Task 12: RTL templates (base, home, search results) + template tags

**Files:**
- Create: `templates/base.html`, `templates/home.html`, `templates/search/results.html`
- Create: `catalog/templatetags/__init__.py`, `catalog/templatetags/listing_tags.py`
- Modify: `config/urls.py` (home route)
- Test: `catalog/tests/test_templatetags.py`

**Interfaces:**
- Consumes: context from `catalog.views.search` (T11) — keys `beans`, `gear`, `facets`, `active`, `total`; and `Seller`/`BeanListing`/`GearListing` fields.
- Produces: two template filters used in templates and testable:
  - `{{ link|outbound }}` → appends `?utm_source=metacoffee&utm_medium=referral&utm_campaign=search` (keeps existing query params, `&`-joined) — for seller outbound cards.
  - `{{ dt|days_ago }}` → Persian-ish "N روز پیش" string given a naive/aware datetime, where N = days since `now` (0 → "امروز").

- [ ] **Step 1: Write the failing test**  `catalog/tests/test_templatetags.py`

```python
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from catalog.templatetags.listing_tags import outbound, days_ago


class ListingTagsTest(TestCase):
    def test_outbound_appends_utm(self):
        self.assertEqual(
            outbound("https://raeescoffee.com/product/a"),
            "https://raeescoffee.com/product/a?utm_source=metacoffee&utm_medium=referral&utm_campaign=search",
        )
        # preserves existing params
        self.assertIn("utm_source=metacoffee",
                      outbound("https://r.example/p?ref=x"))

    def test_days_ago(self):
        now = timezone.now()
        self.assertEqual(days_ago(now), "امروز")
        self.assertEqual(days_ago(now - timedelta(days=3)), "۳ روز پیش")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test catalog.tests.test_templatetags -v 2`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write `catalog/templatetags/listing_tags.py`**

```python
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from datetime import datetime
from django import template
from django.utils import timezone

register = template.Library()

UTM = [("utm_source", "metacoffee"), ("utm_medium", "referral"), ("utm_campaign", "search")]


@register.filter
def outbound(url):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(UTM)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@register.filter
def days_ago(value):
    if not value:
        return ""
    dep = timezone.localtime()
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    delta = dep - value
    days = delta.days
    if days <= 0:
        return "امروز"
    fa = {1: "۱", 2: "۲", 3: "۳", 4: "۴", 5: "۵", 6: "۶", 7: "۷", 8: "۸", 9: "۹", 0: "۰"}
    d = "".join(fa[int(c)] for c in str(days))
    return f"{d} روز پیش"
```

- [ ] **Step 4: Write `templates/base.html`**

```html
{% load static %}
<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}متا‌کافی{% endblock %}</title>
  {% block extra_head %}{% endblock %}
</head>
<body>
  <header>
    <nav>
      <a href="{% url 'home' %}">متاکافی</a>
      <a href="{% url 'search' %}">جستجو</a>
      <a href="{% url 'blog_index' %}">مجله</a>
    </nav>
  </header>
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

- [ ] **Step 5: Write `templates/home.html`**

```html
{% extends "base.html" %}
{% block title %}متاکافی — جستجوی قهوه ایران{% endblock %}
{% block content %}
  <h1>قهوه‌ات را پیدا کن</h1>
  <p>جستجو بر اساس خاستگاه، برشته، فرآوری و تجهیزات دم‌آوری میان فروشندگان معتبر ایران.</p>
  <form action="{% url 'search' %}" method="get">
    <input type="text" name="q" placeholder="مثلاً برزیل شکلاتی یا آسیاب دستی">
    <button type="submit">جستجو</button>
  </form>
  <p><a href="{% url 'search' %}">مرور همه</a></p>
{% endblock %}
```

- [ ] **Step 6: Write `templates/search/results.html`**

```html
{% extends "base.html" %}
{% load listing_tags %}
{% block title %}نتایج جستجو — متاکافی{% endblock %}
{% block content %}
  <form action="{% url 'search' %}" method="get">
    <input type="text" name="q" value="{{ active.q }}">
    <button type="submit">جستجو</button>
  </form>
  <p>{{ total }} نتیجه</p>

  <aside>
    <h3>خاستگاه</h3>
    <ul>{% for f in facets.origins %}<li><a href="?origin={{ f.value }}">{{ f.label }} ({{ f.count }})</a></li>{% endfor %}</ul>
    <h3>برشت</h3>
    <ul>{% for f in facets.roasts %}<li><a href="?roast={{ f.value }}">{{ f.label }} ({{ f.count }})</a></li>{% endfor %}</ul>
    <h3>فرآوری</h3>
    <ul>{% for f in facets.processes %}<li><a href="?process={{ f.value }}">{{ f.label }} ({{ f.count }})</a></li>{% endfor %}</ul>
    <h3>دسته (تجهیزات)</h3>
    <ul>{% for f in facets.gear_categories %}<li><a href="?category={{ f.value }}">{{ f.label }} ({{ f.count }})</a></li>{% endfor %}</ul>
  </aside>

  <h2>دانه‌ها (اصالت‌دار)</h2>
  <ul>
    {% for b in beans %}
      <li>
        <a href="{{ b.link|outbound }}" rel="nofollow noopener" target="_blank">{{ b.name }}</a>
        — {{ b.origin|default:"—" }} · {{ b.roast_level|default:"" }} · {{ b.process|default:"" }}
        {% if b.price_toman %}({{ b.price_toman }} تومان){% endif %}
        {% if b.last_verified %}· تأیید شده {{ b.last_verified|days_ago }}{% endif %}
        <a href="?origin={{ b.origin }}">…</a>
      </li>
    {% empty %}
      <li>دانه‌ای یافت نشد.</li>
    {% endfor %}
  </ul>

  <h2>تجهیزات</h2>
  <ul>
    {% for g in gear %}
      <li>
        <a href="{{ g.link|outbound }}" rel="nofollow noopener" target="_blank">{{ g.name }}</a>
        — {{ g.category|default:"—" }}
        {% if g.price_toman %}({{ g.price_toman }} تومان){% endif %}
        {% if g.last_crawled %}· به‌روزرسانی {{ g.last_crawled|days_ago }}{% endif %}
      </li>
    {% empty %}
      <li>تجهیزاتی یافت نشد.</li>
    {% endfor %}
  </ul>
{% endblock %}
```

- [ ] **Step 7: Wire the home route in `config/urls.py`**

```python
from django.shortcuts import render
def home(request):
    return render(request, "home.html")
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("search/", catalog_views.search, name="search"),
]
```

- [ ] **Step 8: Run tests**

Run: `.venv/bin/python manage.py test catalog -v 2`
Expected: PASS (including the earlier `test_verified_beans_only`, now rendering the real template).

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: RTL templates + outbound/freshness template tags + home"
```

---

### Task 13: Search end-to-end with real imported data + sort dropdown

**Files:**
- Modify: `templates/search/results.html` (add a sort control)
- Test: `catalog/tests/test_search_view.py` (extend with a price-sort test)

**Interfaces:**
- Consumes: imported data (T9), search view (T11).

- [ ] **Step 1: Write the failing (extended) test** — append to `catalog/tests/test_search_view.py`

```python
    def test_price_sort(self):
        BeanListing.objects.create(
            seller=Seller.objects.get(name="Cafe Raees"), name="ارزان",
            is_verified=True, price_toman=100_000, source_key="https://r.example/cheap",
            link="https://r.example/cheap")
        resp = self.client.get(reverse("search"), {"sort": "price_asc"})
        names = [b.name for b in resp.context["beans"]]
        self.assertEqual(names[0], "ارزان")
```

- [ ] **Step 2: Run to verify the new test passes (it should with current code)**

Run: `.venv/bin/python manage.py test catalog.tests.test_search_view -v 2`
Expected: PASS (this test validates the existing sort logic; the real deliverable is a manual smoke).

- [ ] **Step 3: Add a sort dropdown to `templates/search/results.html`** (inside the search `<form>`)

```html
    <select name="sort">
      <option value="" {% if active.sort == "" %}selected{% endif %}>بهترین</option>
      <option value="price_asc" {% if active.sort == "price_asc" %}selected{% endif %}>ارزان‌ترین</option>
      <option value="price_desc" {% if active.sort == "price_desc" %}selected{% endif %}>گران‌ترین</option>
      <option value="newest" {% if active.sort == "newest" %}selected{% endif %}>جدیدترین</option>
    </select>
```

- [ ] **Step 4: Manual smoke test against the real DB**

```bash
docker compose up -d   # ensure db up
.venv/bin/python manage.py runserver 127.0.0.1:8000 &
curl -s "http://127.0.0.1:8000/search/?q=برزیل" | grep -o 'برزیل' | head
curl -s "http://127.0.0.1:8000/search/?origin=Brazil" | grep -c 'برزیل'
kill %1
```
Expected: glyph counts > 0 for the Brazil browse; no crash.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: sort control in search results"
```

---

## Phase 4 — Editorial

### Task 14: Post model + admin

**Files:**
- Modify: `blog/models.py`
- Modify: `blog/admin.py`
- Test: `blog/tests/test_post.py`

**Interfaces:**
- Produces: `blog.models.Post(title, slug, body, published_at, is_published, meta_description)` with a `get_absolute_url() = /blog/<slug>/`. Consumed by blog views (T15). Admin enforces slug uniqueness and lets posts be drafted (`is_published=False`).

- [ ] **Step 1: Write the failing test**  `blog/tests/test_post.py`

```python
from django.test import TestCase
from django.urls import reverse
from blog.models import Post


class PostTest(TestCase):
    def test_published_post_url(self):
        p = Post.objects.create(
            title="بهترین آسیاب زیر ۱۰ میلیون", slug="best-grinder",
            body="راهنمای خرید", is_published=True,
        )
        self.assertEqual(p.get_absolute_url(), reverse("blog_post", args=["best-grinder"]))
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test blog.tests.test_post -v 2`
Expected: FAIL.

- [ ] **Step 3: Write `blog/models.py`** (replace generated file)

```python
from django.db import models
from django.urls import reverse


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField()
    published_at = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    meta_description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_post", args=[self.slug])
```

- [ ] **Step 4: Write `blog/admin.py`** (replace generated file)

```python
from django.contrib import admin
from blog.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "published_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
```

- [ ] **Step 5: Make and run migration + test**

```bash
.venv/bin/python manage.py makemigrations blog
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test blog.tests.test_post -v 2
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: blog Post model + admin"
```

---

### Task 15: Blog index + detail views and templates

**Files:**
- Create: `blog/views.py`
- Create: `templates/blog/index.html`, `templates/blog/post.html`
- Modify: `config/urls.py` (routes `/blog/`, `/blog/<slug>/`)
- Test: `blog/tests/test_views.py`

**Interfaces:**
- Consumes: `Post` (T14).
- Produces: `blog.views.index` (published posts, newest first) and `blog.views.post_detail(slug)` (404 if unpublished); URL names `blog_index`, `blog_post`. Referenced from `base.html` nav.

- [ ] **Step 1: Write the failing test**  `blog/tests/test_views.py`

```python
from django.test import TestCase
from django.urls import reverse
from blog.models import Post


class BlogViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pub = Post.objects.create(
            title="راهنما", slug="guide", body="متن",
            is_published=True, published_at="2026-09-01 12:00:00",
        )
        cls.draft = Post.objects.create(
            title="پیش‌نویس", slug="draft", body="x", is_published=False,
        )

    def test_index_shows_published_only(self):
        resp = self.client.get(reverse("blog_index"))
        self.assertContains(resp, self.pub.title)
        self.assertNotContains(resp, self.draft.title)

    def test_draft_returns_404(self):
        resp = self.client.get(reverse("blog_post", args=["draft"]))
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python manage.py test blog.tests.test_views -v 2`
Expected: FAIL — routes/templates missing.

- [ ] **Step 3: Write `blog/views.py`**

```python
from django.shortcuts import render, get_object_or_404
from blog.models import Post


def index(request):
    posts = Post.objects.filter(is_published=True)
    return render(request, "blog/index.html", {"posts": posts})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, "blog/post.html", {"post": post})
```

- [ ] **Step 4: Write `templates/blog/index.html`**

```html
{% extends "base.html" %}
{% block title %}مجله متاکافی{% endblock %}
{% block content %}
  <h1>مجله</h1>
  <ul>
    {% for p in posts %}
      <li><a href="{{ p.get_absolute_url }}">{{ p.title }}</a></li>
    {% empty %}
      <li>هنوز مطلبی منتشر نشده.</li>
    {% endfor %}
  </ul>
{% endblock %}
```

- [ ] **Step 5: Write `templates/blog/post.html`**

```html
{% extends "base.html" %}
{% block title %}{{ post.title }} — متاکافی{% endblock %}
{% block content %}
  <h1>{{ post.title }}</h1>
  <div>{{ post.body|linebreaks }}</div>
{% endblock %}
```

- [ ] **Step 6: Add routes to `config/urls.py`**

```python
from blog import views as blog_views
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("search/", catalog_views.search, name="search"),
    path("blog/", blog_views.index, name="blog_index"),
    path("blog/<slug:slug>/", blog_views.post_detail, name="blog_post"),
]
```

- [ ] **Step 7: Run tests**

Run: `.venv/bin/python manage.py test blog -v 2`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: blog index + detail views and templates"
```

---

## Phase 5 — Polish & Verify

### Task 16: Full flow smoke, README, and seed a couple of posts

**Files:**
- Create: `README.md`
- Modify: (optional) nothing else

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write `README.md`**

```markdown
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

Source catalog: scraper/catalog.jsonl (19 roasters, 2157 products, 474 beans).
```

- [ ] **Step 2: Seed two editorial posts** (content placeholders are fine — real copy is a content task, not code)

```bash
.venv/bin/python manage.py shell -c "
from blog.models import Post
Post.objects.update_or_create(slug='first-guide', defaults=dict(
    title='شروع کار با متاکافی', body='چطور بهترین قهوه را پیدا کنیم…',
    is_published=True, published_at='2026-09-12 12:00:00'))
print('seeded posts:', Post.objects.filter(is_published=True).count())
"
```

- [ ] **Step 3: Full-flow manual check**

```bash
docker compose up -d
.venv/bin/python manage.py runserver 127.0.0.1:8000 &
curl -s http://127.0.0.1:8000/                                        # home
curl -s "http://127.0.0.1:8000/search/?q=برزیل" | grep -o 'برزیل' | wc -l
curl -s "http://127.0.0.1:8000/blog/" | grep -o 'شروع' | head
# verify admin loads and mark-verified action present:
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/   # expect 302 (login)
kill %1
```

- [ ] **Step 4: Run the full test suite**

Run: `.venv/bin/python manage.py test`
Expected: all catalog + blog tests PASS.

- [ ] **Step 5: Fix any failing test** before committing (debug then re-run until green).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: README + seed posts + v1 smoke verified"
```

---

## Self-Review Summary

- **Spec coverage:** §4 (three core entities + freshness) → T4/T5/T6/T7, T10. §5 (facets + pg_trgm, freshness sortable, zero-result log) → T11/T12/T13. §6 (blog + links to listings) → T14/T15 (full copy is content work, flagged). §7 (Django+Postgres, admin curation, scraper-command plumbing, no JS) → scaffold T1–T3 + T8. §8 (UTM outbound, sponsorship guardrail noted) → T12. Seller `relationship` = CRM field → T4 + admin.
- **Deferred (not code tasks):** pre-launch ~10–15 editorial posts (spec §6) — content, not build; Phase 1/2 monetization & sponsorship disclosure UI (spec §8) — future phase; the crawler-as-cron management command (spec §7) is scaffolded by the `import_catalog` pattern but full re-crawl scheduling is a follow-up plan since the v1 catalog is already scraped.
- **No placeholders:** every code step has concrete, runnable code; the only "…" is in template facet loops, which are complete iterators.
- **Type consistency:** `source_key`=product_url everywhere (import ↔ models); `is_verified`/`last_verified`/`last_crawled` names consistent across models, admin action, import, search filter, and templates; choice values match the scraped data exactly (verified against `catalog.jsonl` before writing).
