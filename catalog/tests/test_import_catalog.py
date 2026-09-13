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
