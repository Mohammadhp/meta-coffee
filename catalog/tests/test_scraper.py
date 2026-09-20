from django.test import TestCase

from scraper import scrape


class WooOriginPriorityTest(TestCase):
    """Origin must come from the strongest signal, not a mashed haystack.

    Regresses the Set Coffee bug: a product whose SEO tag listed other
    origins ("خرید دانه قهوه اتیوپی، ...") was mis-labelled Ethiopia
    despite a dedicated origin attribute saying Guatemala.
    """

    def _item(self, name, cats=(), tags=(), attrs=()):
        return {
            "name": name,
            "categories": [{"name": n} for n in cats],
            "tags": [{"name": n} for n in tags],
            "attributes": [
                {"name": an, "terms": [{"name": t} for t in terms]}
                for an, terms in attrs
            ],
            "prices": {"price": "1690000"},
            "is_in_stock": True,
            "permalink": "https://set-coffee.com/product/x",
            "description": "",
            "short_description": "",
        }

    def test_dedicated_origin_attr_beats_noisy_tags(self):
        item = self._item(
            name="دانه قهوه گواتمالا اسپشیالیتی فراوری نوین (Natural Anaerobic ) مقدار 250 گرم",
            cats=("قهوه اسپشیالیتی",),
            tags=("خرید دانه قهوه اتیوپی، خرید دانه قهوه کلمبیا",),
            attrs=(("خاستگاه", ("گواتمالا",)),),
        )
        self.assertEqual(scrape.parse_woo_item(item, "Set Coffee")["origin"], "Guatemala")

    def test_name_beats_noisy_tags(self):
        item = self._item(
            name="دانه قهوه گواتمالا",
            tags=("خرید دانه قهوه اتیوپی",),
        )
        self.assertEqual(scrape.parse_woo_item(item, "Set Coffee")["origin"], "Guatemala")

    def test_name_still_works_without_attr(self):
        item = self._item(name="قهوه برزیل مدیوم")
        self.assertEqual(scrape.parse_woo_item(item, "Set Coffee")["origin"], "Brazil")