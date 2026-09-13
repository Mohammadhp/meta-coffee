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
