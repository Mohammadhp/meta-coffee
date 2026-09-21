from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from catalog.models import BeanListing, GearListing, SearchQuery, Seller


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
    seller_id = _int(request.GET.get("seller"))
    ftype = request.GET.get("type", "bean")
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

    # seller facets
    seller_rows = (
        bean_base
        .values("seller_id", "seller__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    facets["sellers"] = [
        {"value": str(r["seller_id"]), "label": r["seller__name"], "count": r["count"]}
        for r in seller_rows
    ]

    # apply filters
    if origin:
        beans = beans.filter(origin=origin)
    if roast:
        beans = beans.filter(roast_level=roast)
    if process:
        beans = beans.filter(process=process)
    if fmt:
        beans = beans.filter(format=fmt)
    if seller_id:
        beans = beans.filter(seller_id=seller_id)
    # Bean-level facets narrow results to beans; mixing unrelated gear in is noise.
    if origin or roast or process or fmt or seller_id:
        gear = gear.none()
    if category:
        gear = gear.filter(category=category)
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

    # Counts for the type tabs are taken before the type split, so the
    # inactive tab can still show how many matches it has.
    bean_count = beans.count()
    gear_count = gear.count()

    # Auto-switch to the tab that has results when the active tab is empty.
    if ftype == "gear" and gear_count == 0 and bean_count > 0:
        ftype = "bean"
    elif ftype == "bean" and bean_count == 0 and gear_count > 0:
        ftype = "gear"

    # Mutual exclusivity: looking at one type hides the other.
    if ftype == "gear":
        beans = beans.none()
    else:
        gear = gear.none()

    total = beans.count() + gear.count()
    if q and total == 0:
        SearchQuery.objects.create(query_text=q)

    page_num = _int(request.GET.get("page")) or 1
    page_size = 40
    qs = (gear if ftype == "gear" else beans).order_by("-updated_at")
    paginator = Paginator(qs, page_size)
    try:
        page = paginator.page(page_num)
    except EmptyPage:
        page = paginator.page(1)

    active = {
        "q": q, "origin": origin, "roast": roast, "process": process,
        "format": fmt, "category": category, "type": ftype,
        "min_price": min_price, "max_price": max_price, "sort": sort,
        "seller": str(seller_id) if seller_id else "",
    }
    ctx = {
        "page": page, "facets": facets,
        "active": active, "total": total,
        "bean_count": bean_count, "gear_count": gear_count,
    }
    return render(request, "search/results.html", ctx)


def seller_index(request):
    sellers = Seller.objects.annotate(
        bean_count=Count("beans", filter=Q(beans__is_verified=True)),
        gear_count=Count("gear"),
    ).order_by("name")
    return render(request, "catalog/seller_index.html", {"sellers": sellers})


def seller_detail(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    live = Q(in_stock=True) | Q(in_stock__isnull=True)
    beans = seller.beans.filter(is_verified=True).filter(live).order_by("-updated_at")
    gear = seller.gear.all().order_by("-updated_at")
    return render(request, "catalog/seller_detail.html", {
        "seller": seller,
        "beans": beans,
        "gear": gear,
        "bean_count": beans.count(),
        "gear_count": gear.count(),
    })