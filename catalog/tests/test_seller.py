from django.test import TestCase
from catalog.models import Seller


class SellerTest(TestCase):
    def test_create_defaults_to_indexed_roaster(self):
        s = Seller.objects.create(name="Cafe Raees", site_url="https://raeescoffee.com")
        self.assertEqual(s.relationship, Seller.Relationship.INDEXED)
        self.assertEqual(s.seller_type, Seller.SellerType.ROASTER)
        self.assertEqual(str(s), "Cafe Raees")
