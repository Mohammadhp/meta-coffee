from django.test import TestCase
from django.urls import reverse
from blog.models import Post


class PostTest(TestCase):
    def test_published_post_url(self):
        p = Post.objects.create(
            title="بهترین آسیاب زیر ۱۰ میلیون", slug="best-grinder",
            body="راهنمای خرید", is_published=True,
        )
        self.assertEqual(p.get_absolute_url(), reverse("blog_post", args=["best-grinder"]))