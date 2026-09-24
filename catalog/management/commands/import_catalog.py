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

# Product-name terms that can never be coffee beans. When one appears in
# the name, the record is gear even if a bean signal (roast/process/format)
# was falsely extracted from marketing copy — e.g. a grinder whose name
# says "رنگ طوسی روشن" (light gray) or cleaning powder named "پودر ...".
# "آسیاب" is exempted by the phrase "آسیاب شده" (ground coffee).
GEAR_NAME_TERMS = (
    "آسیاب", "شستشو", "تمیز", "ماگ", "پیچر", "موکاپات", "ترازو",
    "سرور", "پرتافیلتر", "تمپر", "لولر", "کتل", "کتری", "دماسنج",
)


def _looks_like_gear(name):
    n = (name or "").replace("‌", " ")  # ZWNJ -> space
    if "آسیاب" in n and "آسیاب شده" in n:
        return False  # ground coffee, not a grinder
    return any(t in n for t in GEAR_NAME_TERMS)


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
                # Auto-verify policy: a listing is live iff the source reports
                # it in-stock (True) or unknown (None) AND a price was
                # extractable. No price means it can't be purchased, so it's
                # flagged out-of-stock and drops out of the verified catalog.
                price = r.get("price_toman")
                in_stock = r.get("in_stock")
                if price is None:
                    in_stock = False
                live = in_stock is not False
                # Classify as a bean when origin is known OR bean-specific fields
                # are present (blends, decaf etc. may lack origin but still are
                # coffee beans — they have roast_level / process / format).
                # A gear-sounding name vetoes: a "grinder" with a bogus roast
                # extraction is still gear.
                is_bean = not _looks_like_gear(r.get("product_name")) and (
                    r.get("origin")
                    or r.get("roast_level") in BeanListing.RoastLevel.values
                    or r.get("process") in BeanListing.Process.values
                    or r.get("format") in BeanListing.BeansFormat.values
                )
                if is_bean:
                    process = r["process"] if r.get("process") in BeanListing.Process.values else None
                    roast = r["roast_level"] if r.get("roast_level") in BeanListing.RoastLevel.values else None
                    fmt = r["format"] if r.get("format") in BeanListing.BeansFormat.values else None
                    # Cross-table dedup: a product whose classification
                    # flipped gear->bean leaves a stale gear row behind.
                    GearListing.objects.filter(source_key=url).delete()
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
                            "price_toman": price,
                            "price_per_100g": r.get("price_per_100g"),
                            "specialty_score": r.get("specialty_score"),
                            "in_stock": in_stock,
                            "link": url,
                            "image_url": r.get("image_url") or "",
                            "is_verified": live,
                            "last_verified": now if live else None,
                        },
                    )
                    seen_keys.add(url)
                    n_beans += 1
                else:
                    # Cross-table dedup: flipped bean->gear.
                    BeanListing.objects.filter(source_key=url).delete()
                    GearListing.objects.update_or_create(
                        source_key=url,
                        defaults={
                            "seller": seller,
                            "name": r["product_name"],
                            "category": _gear_category(r.get("categories")),
                            "price_toman": price,
                            "in_stock": in_stock,
                            "last_crawled": now,
                            "link": url,
                            "image_url": r.get("image_url") or "",
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
