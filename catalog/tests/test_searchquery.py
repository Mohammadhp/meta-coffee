from django.test import TestCase
from catalog.models import SearchQuery


class SearchQueryTest(TestCase):
    def test_records_query(self):
        q = SearchQuery.objects.create(query_text="برزیل شکلاتی")
        self.assertEqual(q.query_text, "برزیل شکلاتی")
        self.assertIsNotNone(q.created_at)