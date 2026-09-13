from datetime import datetime, timezone

from django.contrib import admin

from catalog.models import Seller, BeanListing, GearListing


def mark_bean_verified(modeladmin, request, queryset):
    """Curation action: flip a draft bean to verified + stamp last_verified."""
    queryset.update(is_verified=True, last_verified=datetime.now(timezone.utc))


mark_bean_verified.short_description = "Mark selected beans as verified"


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
    actions = [mark_bean_verified]


@admin.register(GearListing)
class GearListingAdmin(admin.ModelAdmin):
    list_display = ("name", "seller", "category", "brand", "price_toman", "in_stock", "last_crawled")
    list_filter = ("category", "in_stock")
    search_fields = ("name", "brand")
    list_select_related = ("seller",)
