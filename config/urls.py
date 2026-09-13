from django.contrib import admin
from django.urls import path
from django.shortcuts import render

from catalog import views as catalog_views


def home(request):
    return render(request, "home.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("search/", catalog_views.search, name="search"),
]
