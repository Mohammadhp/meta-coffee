from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.shortcuts import render

from catalog import views as catalog_views
from blog import views as blog_views
from config.sitemaps import SITEMAPS


def home(request):
    return render(request, "home.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("search/", catalog_views.search, name="search"),
    path("sellers/", catalog_views.seller_index, name="seller_index"),
    path("seller/<int:seller_id>/", catalog_views.seller_detail, name="seller_detail"),
    path("blog/", blog_views.index, name="blog_index"),
    path("blog/<slug:slug>/", blog_views.post_detail, name="blog_post"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django.contrib.sitemaps.views.sitemap"),
]
