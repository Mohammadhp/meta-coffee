from django.test import TestCase
from django.urls import reverse
from catalog.models import Seller, BeanListing, GearListing, SearchQuery


class SearchViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = Seller.objects.create(name="Cafe Raees")
        cls.verified = BeanListing.objects.create(
            seller=s, name="برزیل شکلاتی", origin="Brazil",
            process="Natural", roast_level="Medium", price_toman=2_000_000,
            is_verified=True, last_verified=None,
            source_key="https://r.example/v", link="https://r.example/v",
        )
        cls.draft = BeanListing.objects.create(
            seller=s, name="اتیوپی گشا", origin="Ethiopia",
            source_key="https://r.example/d", link="https://r.example/d",
            is_verified=False,
        )
        cls.gear = GearListing.objects.create(
            seller=s, name="آسیاب برقی x", category="grinder",
            source_key="https://r.example/g", link="https://r.example/g",
        )

    def test_verified_beans_only(self):
        resp = self.client.get(reverse("search"))
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.draft.name)

    def test_facet_filter_by_origin(self):
        resp = self.client.get(reverse("search"), {"origin": "Brazil"})
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.gear.name)

    def test_zero_result_is_logged(self):
        self.client.get(reverse("search"), {"q": "چیز ناموجود"})
        self.assertEqual(SearchQuery.objects.filter(query_text="چیز ناموجود").count(), 1)

    def test_default_shows_beans_not_gear(self):
        # looking at beans hides gear (mutual exclusivity, beans = default)
        resp = self.client.get(reverse("search"))
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.gear.name)

    def test_gear_type_shows_gear_not_beans(self):
        resp = self.client.get(reverse("search"), {"type": "gear"})
        self.assertContains(resp, self.gear.name)
        self.assertNotContains(resp, self.verified.name)

    def test_price_sort(self):
        BeanListing.objects.create(
            seller=Seller.objects.get(name="Cafe Raees"), name="ارزان",
            is_verified=True, price_toman=100_000, source_key="https://r.example/cheap",
            link="https://r.example/cheap")
        resp = self.client.get(reverse("search"), {"sort": "price_asc"})
        names = [b.name for b in resp.context["page"]]
        self.assertEqual(names[0], "ارزان")

    def test_auto_switches_to_gear_when_beans_empty(self):
        """A gear-only search on the default bean tab auto-switches to gear."""
        resp = self.client.get(reverse("search"), {"q": "آسیاب"})
        self.assertEqual(resp.context["active"]["type"], "gear")
        self.assertContains(resp, self.gear.name)
        self.assertNotContains(resp, self.verified.name)

    def test_auto_switches_to_beans_when_gear_empty(self):
        """A bean-only search on the gear tab auto-switches to beans."""
        # "شکلاتی" is only in the bean name, not in the gear name
        resp = self.client.get(reverse("search"),
                               {"q": "شکلاتی", "type": "gear"})
        self.assertEqual(resp.context["active"]["type"], "bean")
        self.assertContains(resp, self.verified.name)
        self.assertNotContains(resp, self.gear.name)

    def test_no_auto_switch_when_both_have_results(self):
        """When both tabs have results, stay on the requested tab."""
        # "قهوه" isn't in either name, but both are the only items so
        # trigram might match.  Use default (beans) and verify it stays.
        resp = self.client.get(reverse("search"))
        # Default tab is bean, both have results, should stay on bean
        self.assertEqual(resp.context["active"]["type"], "bean")