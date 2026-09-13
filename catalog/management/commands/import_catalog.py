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