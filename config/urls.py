from django.contrib import admin
from django.urls import path
from django.http import HttpResponse


def index(request):
    return HttpResponse("Meta-Coffee is up")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index),
]
