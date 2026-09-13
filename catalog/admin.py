from django.contrib import admin

from catalog.models import Seller


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("name", "seller_type", "city", "site_url", "relationship")
    list_filter = ("seller_type", "relationship")
    search_fields = ("name",)
