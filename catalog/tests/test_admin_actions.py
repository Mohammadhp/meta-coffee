from django.test import TestCase
from catalog.admin import mark_bean_verified
from catalog.models import Seller, BeanListing
from django.contrib.admin.sites import AdminSite
from django.contrib.admin import ModelAdmin


class MarkVerifiedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        s = Seller.objects.create(name="R")
        cls.bean = BeanListing.objects.create(
            seller=s, name="b", source_key="https://r.example/b"
        )

    def test_action_sets_verified_and_stamp(self):
        qs = BeanListing.objects.filter(pk=self.bean.pk)
        mark_bean_verified(ModelAdmin(BeanListing, AdminSite()), None, qs)
        self.bean.refresh_from_db()
        self.assertTrue(self.bean.is_verified)
        self.assertIsNotNone(self.bean.last_verified)
