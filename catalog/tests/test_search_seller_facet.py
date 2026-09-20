from django.test import TestCase
from django.urls import reverse

from catalog.models import Seller, BeanListing, GearListing


class SearchSellerFacetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.s1 = Seller.objects.create(name="Cafe Raees")
        cls.s2 = Seller.objects.create(name="Set Coffee")
        cls.bean_s1_a = BeanListing.objects.create(
            seller=cls.s1, name="برزیل شکلاتی", origin="Brazil",
            is_verified=True,
            source_key="https://r.example/s1a", link="https://r.example/s1a",
        )
        cls.bean_s1_b = BeanListing.objects.create(
            seller=cls.s1, name="کلمبیا کارامل", origin="Colombia",
            is_verified=True,
            source_key="https://r.example/s1b", link="https://r.example/s1b",
        )
        cls.bean_s2 = BeanListing.objects.create(
            seller=cls.s2, name="اتیوپی گشا", origin="Ethiopia",
            is_verified=True,
            source_key="https://r.example/s2", link="https://r.example/s2",
        )
        cls.gear = GearListing.objects.create(
            seller=cls.s1, name="آسیاب برقی", category="grinder",
            source_key="https://r.example/g", link="https://r.example/g",
        )

    def test_seller_facet_appears_with_counts(self):
        resp = self.client.get(reverse("search"))
        self.assertContains(resp, "فروشنده")
        self.assertContains(resp, self.s1.name)
        self.assertContains(resp, self.s2.name)
        # s1 has 2 verified beans, s2 has 1
        self.assertContains(resp, "2")
        self.assertContains(resp, "1")

    def test_seller_filter_narrows_to_single_seller(self):
        resp = self.client.get(reverse("search"), {"seller": self.s2.id})
        self.assertContains(resp, self.bean_s2.name)
        self.assertNotContains(resp, self.bean_s1_a.name)
        self.assertNotContains(resp, self.bean_s1_b.name)

    def test_seller_filter_is_bean_only_hides_gear(self):
        resp = self.client.get(reverse("search"), {"seller": self.s1.id})
        self.assertContains(resp, self.bean_s1_a.name)
        self.assertNotContains(resp, self.gear.name)
        # active type must resolve to bean (gear is emptied)
        self.assertEqual(resp.context["active"]["type"], "bean")

    def test_seller_filter_preserved_in_sort_form(self):
        resp = self.client.get(reverse("search"), {"seller": self.s2.id})
        self.assertContains(
            resp, f'name="seller" value="{self.s2.id}"'
        )

    def test_active_seller_marked_in_facet(self):
        resp = self.client.get(reverse("search"), {"seller": self.s2.id})
        self.assertContains(resp, 'class="active"')

    def test_invalid_seller_id_ignored(self):
        resp = self.client.get(reverse("search"), {"seller": "abc"})
        self.assertEqual(resp.status_code, 200)
        # still shows all three beans (filter ignored)
        self.assertContains(resp, self.bean_s1_a.name)
        self.assertContains(resp, self.bean_s2.name)
