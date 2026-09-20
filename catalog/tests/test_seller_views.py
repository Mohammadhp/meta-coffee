from django.test import TestCase
from django.urls import reverse

from catalog.models import Seller, BeanListing, GearListing


class SellerViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s1 = Seller.objects.create(
            name="Cafe Raees", site_url="https://raeescoffee.com",
        )
        cls.s2 = Seller.objects.create(
            name="Set Coffee", site_url="https://set-coffee.com",
        )
        cls.bean = BeanListing.objects.create(
            seller=cls.s1, name="برزیل شکلاتی", origin="Brazil",
            is_verified=True, price_toman=2_000_000,
            source_key="https://r.example/b", link="https://r.example/b",
        )
        cls.draft = BeanListing.objects.create(
            seller=cls.s1, name="پیش‌نویس", origin="Ethiopia",
            is_verified=False,
            source_key="https://r.example/d", link="https://r.example/d",
        )
        cls.gear = GearListing.objects.create(
            seller=cls.s1, name="آسیاب برقی", category="grinder",
            source_key="https://r.example/g", link="https://r.example/g",
        )

    def test_seller_index_200(self):
        resp = self.client.get(reverse("seller_index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.s1.name)
        self.assertContains(resp, self.s2.name)

    def test_seller_index_counts(self):
        resp = self.client.get(reverse("seller_index"))
        self.assertContains(resp, "1 دانه")

    def test_seller_detail_200(self):
        resp = self.client.get(
            reverse("seller_detail", kwargs={"seller_id": self.s1.id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.s1.name)
        self.assertContains(resp, self.bean.name)

    def test_seller_detail_404(self):
        resp = self.client.get(
            reverse("seller_detail", kwargs={"seller_id": 9999})
        )
        self.assertEqual(resp.status_code, 404)

    def test_seller_detail_hides_unverified_beans(self):
        resp = self.client.get(
            reverse("seller_detail", kwargs={"seller_id": self.s1.id})
        )
        self.assertContains(resp, self.bean.name)
        self.assertNotContains(resp, self.draft.name)

    def test_seller_detail_shows_gear(self):
        resp = self.client.get(
            reverse("seller_detail", kwargs={"seller_id": self.s1.id})
        )
        self.assertContains(resp, self.gear.name)

    def test_search_results_link_seller_name(self):
        resp = self.client.get(reverse("search"))
        url = reverse("seller_detail", kwargs={"seller_id": self.s1.id})
        self.assertContains(resp, url)
