from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from catalog.templatetags.listing_tags import outbound, days_ago, fa_price


class ListingTagsTest(TestCase):
    def test_outbound_appends_utm(self):
        self.assertEqual(
            outbound("https://raeescoffee.com/product/a"),
            "https://raeescoffee.com/product/a?utm_source=metacoffee&utm_medium=referral&utm_campaign=search",
        )
        # preserves existing params
        self.assertIn("utm_source=metacoffee",
                      outbound("https://r.example/p?ref=x"))

    def test_days_ago(self):
        now = timezone.now()
        self.assertEqual(days_ago(now), "امروز")
        self.assertEqual(days_ago(now - timedelta(days=3)), "۳ روز پیش")

    def test_fa_price(self):
        self.assertEqual(fa_price(2300000), "۲٬۳۰۰٬۰۰۰")
        self.assertEqual(fa_price(None), "")
        self.assertEqual(fa_price("x"), "")