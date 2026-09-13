from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Count, Q
from django.shortcuts import render

from catalog.models import BeanListing, GearListing, SearchQuery


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _facets(qs, field):
    rows = (
        qs.exclude(**{field: None})
        .exclude(**{field: ""})
        .values(field)
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [{"value": r[field], "label": r[field], "count": r["count"]} for r in rows]


def search(request):
    q = request.GET.get("q", "").strip()
    origin = request.GET.get("origin", "")
    roast = request.GET.get("roast", "")
    process = request.GET.get("process", "")
    fmt = request.GET.get("format", "")
    category = request.GET.get("category", "")
    ftype = request.GET.get("type", "")
    min_price = _int(request.GET.get("min_price"))
    max_price = _int(request.GET.get("max_price"))
    sort = request.GET.get("sort", "")

    beans = BeanListing.objects.filter(
        is_verified=True
    ).filter(Q(in_stock=True) | Q(in_stock__isnull=True))
    gear = GearListing.objects.all()

    if q:
        beans = beans.annotate(_sim=TrigramSimilarity("name", q)).filter(_sim__gt=0.2)
        gear = gear.annotate(_sim=TrigramSimilarity("name", q)).filter(_sim__gt=0.2)
        beans = beans.order_by("-_sim")
        gear = gear.order_by("-_sim")

    # facets computed from the full verified catalog (independent of filters)
    bean_base = BeanListing.objects.filter(is_verified=True)
    facets = {
        "origins": _facets(bean_base, "origin"),
        "roasts": _facets(bean_base, "roast_level"),
        "processes": _facets(bean_base, "process"),
        "formats": _facets(bean_base, "format"),
        "gear_categories": _facets(GearListing.objects.all(), "category"),
    }

    # apply filters
    if origin:
        beans = beans.filter(origin=origin)
    if roast:
        beans = beans.filter(roast_level=roast)
    if process:
        beans = beans.filter(process=process)
    if fmt:
        beans = beans.filter(format=fmt)
    # Bean-level facets narrow results to beans; mixing unrelated gear in is noise.
    if origin or roast or process or fmt:
        gear = gear.none()
    if category:
        gear = gear.filter(category=category)
    if ftype == "bean":
        gear = gear.none()
    elif ftype == "gear":
        beans = beans.none()
    if min_price is not None:
        beans = beans.filter(price_toman__gte=min_price)
        gear = gear.filter(price_toman__gte=min_price)
    if max_price is not None:
        beans = beans.filter(price_toman__lte=max_price)
        gear = gear.filter(price_toman__lte=max_price)
    if sort == "price_asc":
        beans, gear = beans.order_by("price_toman"), gear.order_by("price_toman")
    elif sort == "price_desc":
        beans, gear = beans.order_by("-price_toman"), gear.order_by("-price_toman")
    elif sort == "newest":
        beans, gear = beans.order_by("-updated_at"), gear.order_by("-updated_at")

    total = beans.count() + gear.count()
    if q and total == 0:
        SearchQuery.objects.create(query_text=q)

    active = {
        "q": q, "origin": origin, "roast": roast, "process": process,
        "format": fmt, "category": category, "type": ftype,
        "min_price": min_price, "max_price": max_price, "sort": sort,
    }
    ctx = {
        "beans": beans[:60], "gear": gear[:60], "facets": facets,
        "active": active, "total": total,
    }
    return render(request, "search/results.html", ctx)