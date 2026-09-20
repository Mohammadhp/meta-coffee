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
        # in_stock=False -> not auto-verified
        self.assertFalse(BeanListing.objects.get().is_verified)
        self.assertIsNone(BeanListing.objects.get().last_verified)
        self.assertEqual(GearListing.objects.count(), 1)
        g = GearListing.objects.get()
        self.assertEqual(g.category, "grinder")   # from "آسیاب" in categories
        self.assertIsNotNone(g.last_crawled)
        self.assertIn("1 seller", out.getvalue())

    def _bean(self, roaster="Cafe Raees", url="https://raeescoffee.com/product/a", **kw):
        rec = {
            "roaster": roaster, "product_name": "قهوه مدیوم",
            "origin": "Colombia", "process": None, "roast_level": "Medium",
            "format": "Whole bean", "weight_g": 500.0, "price_toman": 2300000,
            "price_per_100g": 460000.0, "specialty_score": None, "in_stock": True,
            "categories": "", "product_url": url, "description": "x",
        }
        rec.update(kw)
        return rec

    def test_auto_verifies_in_stock_and_unknown(self):
        path = self._write([
            self._bean(url=".../a", in_stock=True),
            self._bean(url=".../b", in_stock=None),
            self._bean(url=".../c", in_stock=False),
        ])
        call_command("import_catalog", file=path, stdout=io.StringIO())
        by_url = {b.source_key: b for b in BeanListing.objects.all()}
        self.assertTrue(by_url[".../a"].is_verified)
        self.assertIsNotNone(by_url[".../a"].last_verified)
        self.assertTrue(by_url[".../b"].is_verified)  # unknown stock still live
        self.assertFalse(by_url[".../c"].is_verified)
        self.assertIsNone(by_url[".../c"].last_verified)

    def test_reimport_does_not_clobber_verified(self):
        bean = self._bean(in_stock=True)
        call_command("import_catalog", file=self._write([bean]), stdout=io.StringIO())
        call_command("import_catalog", file=self._write([bean]), stdout=io.StringIO())
        b = BeanListing.objects.get()
        self.assertTrue(b.is_verified)
        self.assertIsNotNone(b.last_verified)

    def test_stale_marked_out_of_stock(self):
        # two beans live; second import keeps only the first
        call_command("import_catalog", file=self._write([
            self._bean(url=".../a"), self._bean(url=".../b"),
        ]), stdout=io.StringIO())
        out = io.StringIO()
        call_command("import_catalog", file=self._write([
            self._bean(url=".../a"),
        ]), stdout=out)
        self.assertTrue(BeanListing.objects.get(source_key=".../a").is_verified)
        b = BeanListing.objects.get(source_key=".../b")
        self.assertFalse(b.in_stock)
        self.assertFalse(b.is_verified)
        self.assertIn("1 marked out-of-stock", out.getvalue())

    def test_site_down_skips_stale(self):
        call_command("import_catalog", file=self._write([
            self._bean(roaster="Cafe Raees", url=".../a"),
        ]), stdout=io.StringIO())
        out = io.StringIO()
        # this run has a different roaster -> Cafe Raees returns zero records
        call_command("import_catalog", file=self._write([
            self._bean(roaster="Vaka Coffee", url=".../v"),
        ]), stdout=out)
        a = BeanListing.objects.get(source_key=".../a")
        self.assertTrue(a.in_stock)
        self.assertIn("skip stale for 'Cafe Raees'", out.getvalue())
