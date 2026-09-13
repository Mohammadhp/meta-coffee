from django.db import models
from django.urls import reverse


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    body = models.TextField()
    published_at = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)
    meta_description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_post", args=[self.slug])