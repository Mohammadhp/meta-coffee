from django.test import TestCase
from django.urls import reverse
from blog.models import Post


class BlogViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pub = Post.objects.create(
            title="راهنما", slug="guide", body="متن",
            is_published=True, published_at="2026-09-01 12:00:00",
        )
        cls.draft = Post.objects.create(
            title="پیش‌نویس", slug="draft", body="x", is_published=False,
        )

    def test_index_shows_published_only(self):
        resp = self.client.get(reverse("blog_index"))
        self.assertContains(resp, self.pub.title)
        self.assertNotContains(resp, self.draft.title)

    def test_draft_returns_404(self):
        resp = self.client.get(reverse("blog_post", args=["draft"]))
        self.assertEqual(resp.status_code, 404)