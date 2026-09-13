from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from django import template
from django.utils import timezone

register = template.Library()

UTM = [("utm_source", "metacoffee"), ("utm_medium", "referral"), ("utm_campaign", "search")]
FA_DIGITS = {"0": "۰", "1": "۱", "2": "۲", "3": "۳", "4": "۴",
             "5": "۵", "6": "۶", "7": "۷", "8": "۸", "9": "۹"}


@register.filter
def outbound(url):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update(UTM)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@register.filter
def days_ago(value):
    if not value:
        return ""
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    delta = timezone.now() - value
    days = delta.days
    if days <= 0:
        return "امروز"
    return f"{''.join(FA_DIGITS[c] for c in str(days))} روز پیش"