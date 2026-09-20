from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Seller
from blog.models import Post


class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["home", "search", "seller_index", "blog_index"]

    def location(self, item):
        return reverse(item)


class SellerSitemap(Sitemap):
    priority = 0.6
    changefreq = "daily"

    def items(self):
        return Seller.objects.order_by("id")

    def location(self, obj):
        return reverse("seller_detail", args=[obj.id])


class BlogSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Post.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.published_at


SITEMAPS = {
    "static": StaticSitemap,
    "sellers": SellerSitemap,
    "blog": BlogSitemap,
}
