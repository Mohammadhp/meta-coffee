import json
import os
import shutil
import tempfile
from unittest import mock

from django.test import TestCase
from django.core.management import call_command

from catalog.models import BeanListing

OUT = "scraper/catalog.jsonl"


class SyncCatalogTest(TestCase):
    def setUp(self):
        # don't clobber the real catalog on disk
        if os.path.exists(OUT):
            shutil.copy(OUT, OUT + ".bak")

    def tearDown(self):
        if os.path.exists(OUT + ".bak"):
            shutil.move(OUT + ".bak", OUT)

    def test_scrapes_then_imports(self):
        # A fake catalog that sync_catalog will import after "scraping".
        rec = {
            "roaster": "Cafe Raees", "product_name": "قهوه مدیوم",
            "origin": "Colombia", "process": None, "roast_level": "Medium",
            "format": "Whole bean", "weight_g": 500.0, "price_toman": 2300000,
            "price_per_100g": 460000.0, "specialty_score": None,
            "in_stock": True, "categories": "",
            "product_url": "https://raeescoffee.com/product/a", "description": "x",
        }
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

        def fake_run(cmd, **kwargs):
            # copy the fake catalog to where the scraper would have written it
            with open("scraper/catalog.jsonl", "w", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            return mock.Mock(returncode=0)

        with mock.patch("catalog.management.commands.sync_catalog.subprocess.run", fake_run):
            call_command("sync_catalog", stdout=None, stderr=None)

        self.assertEqual(BeanListing.objects.count(), 1)
        self.assertTrue(BeanListing.objects.get().is_verified)
