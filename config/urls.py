from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

from catalog import views as catalog_views


def index(request):
    return HttpResponse("Meta-Coffee is up")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("search/", catalog_views.search, name="search"),
    path("", index),
]
