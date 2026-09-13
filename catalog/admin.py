from django.contrib import admin

from catalog.models import Seller, BeanListing


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("name", "seller_type", "city", "site_url", "relationship")
    list_filter = ("seller_type", "relationship")
    search_fields = ("name",)


@admin.register(BeanListing)
class BeanListingAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "origin", "process", "roast_level",
                    "price_toman", "in_stock", "is_verified", "last_verified")
    list_filter = ("origin", "process", "roast_level", "is_verified", "in_stock")
    search_fields = ("name", "origin")
    list_select_related = ("seller",)
