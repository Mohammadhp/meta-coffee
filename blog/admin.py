from django.contrib import admin
from blog.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "published_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}