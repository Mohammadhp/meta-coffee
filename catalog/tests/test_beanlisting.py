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
