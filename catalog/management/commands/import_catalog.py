import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db.models import Q

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
    help = (
        "Import scraper/catalog.jsonl into Sellers + Bean/Gear listings "
        "(idempotent). In-stock/unknown-stock beans are auto-verified; "
        "listings that vanished from a still-active seller's site are marked "
        "out-of-stock."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", default="scraper/catalog.jsonl")
        parser.add_argument(
            "--no-stale",
            action="store_true",
            help="Skip marking vanished listings as out-of-stock.",
        )

    def handle(self, *args, **opts):
        path = opts["file"]
        now = datetime.now(timezone.utc)
        n_sellers = n_beans = n_gear = 0
        seen_sellers = set()
        seen_keys = set()
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                domain = urlparse(r.get("product_url", "")).netloc
                site_url = f"https://{domain}" if domain else ""
                seller, _ = Seller.objects.update_or_create(
                    name=r["roaster"],
                    defaults={
                        "site_url": site_url,
                        "relationship": Seller.Relationship.INDEXED,
                    },
                )
                seen_sellers.add(r["roaster"])
                url = r.get("product_url", "")
                # Auto-verify policy: a bean is live iff the source reports it
                # in-stock (True) or unknown (None). Explicitly out-of-stock
                # (False) beans drop out of the verified catalog.
                live = r.get("in_stock") is not False
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
                            "is_verified": live,
                            "last_verified": now if live else None,
                        },
                    )
                    seen_keys.add(url)
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
                    seen_keys.add(url)
                    n_gear += 1
        n_sellers = Seller.objects.count()
        n_stale = 0 if opts["no_stale"] else self._mark_stale(seen_sellers, seen_keys)
        self.stdout.write(
            f"Imported: {n_sellers} sellers, {n_beans} beans, {n_gear} gear, "
            f"{n_stale} marked out-of-stock"
        )

    def _mark_stale(self, seen_sellers, seen_keys):
        """Mark listings that vanished from a still-active seller's site.

        A seller that returned *zero* records this run is assumed to have
        failed transiently (site down / changed), so its listings are left
        untouched and a warning is emitted instead.
        """
        if not seen_keys:
            return 0
        n = 0
        live = Q(in_stock=True) | Q(in_stock__isnull=True)
        for seller in Seller.objects.all():
            if seller.name not in seen_sellers:
                if seller.beans.exists() or seller.gear.exists():
                    self.stdout.write(self.style.WARNING(
                        f"skip stale for '{seller.name}': no records this run"
                    ))
                continue
            n += seller.beans.filter(live).exclude(source_key__in=seen_keys).update(
                in_stock=False, is_verified=False, last_verified=None
            )
            n += seller.gear.filter(live).exclude(source_key__in=seen_keys).update(
                in_stock=False
            )
        return n
