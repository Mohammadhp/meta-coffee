#!/usr/bin/env python
"""Meta-Coffee catalog scraper.

Fetches product catalogs for prominent Tehran coffee roasters and emits a
normalized JSONL catalog (one product per line). See README note in the repo
for rate-limiting / robots policy; this tool is website-only and polite.

Usage:
    .venv/bin/python scraper/scrape.py
"""
import json
import re
import sys
import time
from urllib.parse import urljoin

import httpx

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

OUT = "scraper/catalog.jsonl"

# ---------------------------------------------------------------------------
# Site registry. type selects the fetch strategy.
# ---------------------------------------------------------------------------
SITES = [
    # WooCommerce via /wp-json/wc/store/v1/products (public)
    {"roaster": "Cafe Raees", "base": "https://raeescoffee.com", "type": "woo"},
    {"roaster": "Emkan Roastery", "base": "https://emkan-coffee.com", "type": "woo"},
    {"roaster": "Vaka Coffee", "base": "https://vakacoffee.com", "type": "woo"},
    {"roaster": "Farda Roastery", "base": "https://fardaroastery.ir", "type": "woo"},
    {"roaster": "Erido Coffee", "base": "https://eridocoffee.com", "type": "woo"},
    {"roaster": "Houfer Coffee", "base": "https://houfercoffee.com", "type": "woo"},
    {"roaster": "Bunas", "base": "https://bunas.ir", "type": "woo"},
    {"roaster": "Xav Coffee Factory", "base": "https://xav.coffee", "type": "woo"},
    {"roaster": "Rei Coffee Roasters", "base": "https://rei.coffee", "type": "woo"},
    {"roaster": "MeCafe Roasters", "base": "https://mecafe.me", "type": "woo"},
    {"roaster": "Garneek Coffee Workshop", "base": "https://garneekcoffee.com", "type": "woo"},
    {"roaster": "Kazhvan Coffee", "base": "https://kazhvancoffee.com", "type": "woo"},
    {"roaster": "Set Coffee", "base": "https://set-coffee.com", "type": "woo"},
    {"roaster": "Redpill Roastery", "base": "https://redpillroastery.coffee", "type": "woo"},
    {"roaster": "Moa Coffee", "base": "https://moa.coffee", "type": "woo"},
    # Luya uses the older store endpoint
    {"roaster": "Luya Coffee", "base": "https://luyacoffee.com", "type": "woo-old"},
    # Lamiz: store API under-reports (33 vs 187); use wp/v2 for full list.
    {"roaster": "Lamiz Coffee", "base": "https://lamizcoffee.com", "type": "woo-v2only"},
    # Custom / non-WP
    {"roaster": "Rio", "base": "https://www.rio.coffee", "type": "rio"},
    {"roaster": "Lemm Coffee", "base": "https://lemm.coffee", "type": "lemm"},
    {"roaster": "Sam Coffee Roasters", "base": "https://www.samcoffeeroasters.com", "type": "sam"},
    {"roaster": "TDS Roastery", "base": "https://www.tds-roastery.com", "type": "tds"},
]

# Persian digit normalization
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def fa_to_en(s):
    return str(s).translate(FA_DIGITS)


# ---------------------------------------------------------------------------
# Helpers for origin / process / roast / weight extraction
# ---------------------------------------------------------------------------
ORIGIN_MAP = {
    "brazil": "Brazil", "برزیل": "Brazil",
    "ethiopia": "Ethiopia", "اتیوپی": "Ethiopia", "اتیوپیا": "Ethiopia",
    "colombia": "Colombia", "کلمبیا": "Colombia",
    "guatemala": "Guatemala", "گواتمالا": "Guatemala",
    "kenya": "Kenya", "کنیا": "Kenya",
    "indonesia": "Indonesia", "اندونزی": "Indonesia",
    "sumatra": "Indonesia", "سوماترا": "Indonesia",
    "uganda": "Uganda", "اوگاندا": "Uganda",
    "tanzania": "Tanzania", "تانزانیا": "Tanzania",
    "mexico": "Mexico", "مکزیک": "Mexico",
    "costa rica": "Costa Rica", "کاستاریکا": "Costa Rica",
    "panama": "Panama", "پاناما": "Panama",
    "peru": "Peru", "پرو": "Peru",
    "honduras": "Honduras", "هندوراس": "Honduras",
    "el salvador": "El Salvador", "السالوادور": "El Salvador",
    "vietnam": "Vietnam", "ویتنام": "Vietnam",
    "congo": "DR Congo", "کنگو": "DR Congo",
    "laos": "Laos", "لائوس": "Laos",
    "rwanda": "Rwanda", "رواندا": "Rwanda",
    "burundi": "Burundi", "بوروندی": "Burundi",
    "nicaragua": "Nicaragua", "نیکاراگوئه": "Nicaragua",
    "bolivia": "Bolivia", "بولیوی": "Bolivia",
    "yemen": "Yemen", "یمن": "Yemen",
}

PROCESS_TERMS = {
    "natural": "Natural", "نچرال": "Natural", "طبیعی": "Natural",
    "washed": "Washed", "واشد": "Washed", "شسته": "Washed",
    "honey": "Honey", "هانی": "Honey", "عسلی": "Honey",
    "anaerobic": "Anaerobic", "اناروبیک": "Anaerobic", "بی‌هوازی": "Anaerobic",
    "تخمیر هوازی": "Aerobic Fermentation",
}

ROAST_TERMS = {
    "light": "Light", "لایت": "Light", "روشن": "Light",
    "medium": "Medium", "مدیوم": "Medium", "متوسط": "Medium",
    "dark": "Dark", "دارک": "Dark", "تیره": "Dark",
    "omni": "Omni",
}

FORMAT_TERMS = {
    "whole bean": "Whole bean", "دان": "Whole bean", "دانه": "Whole bean", "beans": "Whole bean",
    "ground": "Ground", "پودر": "Ground", "اسپرسو (پودر)": "Ground",
    "capsule": "Capsule", "کپسول": "Capsule", "پاد": "Pod", "pod": "Pod",
}


def _word_match(keyword, text):
    """Match *keyword* as a whole word in *text*, not as a substring.

    "یمن" matches ``قهوه یمن`` but not ``آندیمند``.
    ``\\w`` does not cover Persian letters, so the boundary is any
    ASCII letter + the Persian Unicode block (U+0600–U+06FF)."""
    kw = re.escape(keyword.lower())
    # letter chars on either side → substring, not a standalone word
    boundary = r"(?<![a-z؀-ۿ])"
    return bool(re.search(boundary + kw + boundary, text.lower()))


def _extract_term(term_map, *texts):
    """Return the first mapped value whose key appears as a whole word in *texts*."""
    for text in texts:
        if not text:
            continue
        for key, val in term_map.items():
            if _word_match(key, text):
                return val
    return None


def extract_origin(*texts):
    return _extract_term(ORIGIN_MAP, *texts)


def extract_process(*texts):
    return _extract_term(PROCESS_TERMS, *texts)


def extract_roast(*texts):
    return _extract_term(ROAST_TERMS, *texts)


def extract_format(*texts):
    return _extract_term(FORMAT_TERMS, *texts)


FA_WORD_NUM = {
    "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6,
    "هفت": 7, "هشت": 8, "نه": 9, "ده": 10, "نیم": 0.5,
}


def extract_weight_g(*texts):
    hay = " ".join(t for t in texts if t)
    hay = fa_to_en(hay)
    # "250g" / "250 gr" / "250 گرم" / "250 گرمی" / "۲۵۰"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|gr|گرم|گرمی|گرام)", hay)
    if m:
        return float(m.group(1))
    # "1kg" / "۱ کیلو" / "کیلوگرم"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|کیلو|کیلوگرم)", hay)
    if m:
        return float(m.group(1)) * 1000
    # Persian word-number weights: "شش کیلوگرمی", "یک کیلویی", "نیم کیلو"
    m = re.search(r"(یک|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|نیم)\s*(?:کیلو|kg)", hay)
    if m:
        return FA_WORD_NUM[m.group(1)] * 1000
    # bare weight in product title like "250" alongside "گرمی" already caught
    return None


def parse_price(raw):
    """Return int toman or None (treat 0 / non-numeric as None)."""
    if raw is None:
        return None
    s = fa_to_en(str(raw)).replace(",", "").replace("٬", "")
    m = re.search(r"(\d+)", s)
    v = int(m.group(1)) if m else None
    return v if v else None


def extract_labeled_fields(desc):
    """Pull origin/process/roast/score from explicit labeled bullets like
    '• خاستگاه: اتیوپی' or 'روش فرآوری: تخمیر هوازی'. High-precision; used for
    sites whose only structured signal is the description (e.g. Sam)."""
    plain = re.sub(r"<[^>]+>", " ", desc or "")
    lines = [fa_to_en(l).strip() for l in re.split(r"[\n\r•●▪|]+", plain)]
    out = {}
    for line in lines:
        if "خاستگاه" in line or "مبدا" in line or "origin" in line.lower():
            out.setdefault("origin", extract_origin(line))
        elif "فرآوری" in line or "پروسس" in line or "process" in line.lower():
            out.setdefault("process", extract_process(line))
        elif "رست" in line or "roast" in line.lower():
            out.setdefault("roast", extract_roast(line))
        elif "امتیاز" in line or "کیو" in line or "score" in line.lower() or "sca" in line.lower():
            m = re.search(r"(\d{2,3})\s*[-–]?\s*(\d{2,3})?", line)
            if m:
                out.setdefault("score", float(m.group(1)))
    return out


# ---------------------------------------------------------------------------
# WooCommerce (store API) strategy
# ---------------------------------------------------------------------------
def fetch_woo(client, site, endpoint="/wp-json/wc/store/v1/products"):
    base = site["base"].rstrip("/")
    items, page = [], 1
    while True:
        r = client.get(f"{base}{endpoint}", params={"per_page": 100, "page": page})
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)
        total = int(r.headers.get("x-wp-total", "0"))
        if len(items) >= total:
            break
        page += 1
        time.sleep(0.15)
    return items


def parse_woo_item(item, roaster):
    name = item.get("name") or ""
    prices = item.get("prices") or {}
    price = parse_price(prices.get("price"))
    cats = [c.get("name", "") for c in (item.get("categories") or [])]
    tags = [t.get("name", "") for t in (item.get("tags") or [])]
    attrs = item.get("attributes") or []
    attr_texts = []
    attr_by_name = {}
    for a in attrs:
        an = a.get("name", "")
        terms = [t.get("name", "") for t in (a.get("terms") or [])]
        if terms:
            attr_by_name[an] = terms
            attr_texts.extend(terms)
    desc = item.get("description") or ""
    short = item.get("short_description") or ""
    text = " ".join([name] + cats + tags + attr_texts)

    # Weight from attributes first, then name.
    weight = None
    for an, terms in attr_by_name.items():
        if any(k in an for k in ("وزن", "weight", "گرم")):
            weight = extract_weight_g(" ".join(terms))
            if weight:
                break
    if weight is None:
        weight = extract_weight_g(name, " ".join(attr_texts))

    # Origin by signal strength: a dedicated origin attribute ("خاستگاه") and
    # the product name are trustworthy; categories/tags are only a fallback,
    # since SEO tags often list many origins ("خرید دانه قهوه اتیوپی، ...").
    origin = None
    for an, terms in attr_by_name.items():
        if any(k in an for k in ("خاستگاه", "مبدا", "origin", "منشا")):
            origin = extract_origin(*terms)
            if origin:
                break
    if not origin:
        origin = extract_origin(name)
    if not origin:
        origin = extract_origin(*cats, *tags, *attr_texts)
    # process/roast are only trusted from structured sources (name, attributes,
    # categories) — never from free-form description, which is where false
    # positives ("natural flavors", "medium body") come from.
    process = extract_process(name, *attr_texts, *cats, *tags)
    roast = extract_roast(name, *attr_texts, *cats, *tags)
    fmt = extract_format(name, *cats, *attr_texts)

    in_stock = bool(item.get("is_in_stock"))
    image_url = ((item.get("images") or [{}])[0].get("src")) or None

    return {
        "roaster": roaster,
        "product_name": name.strip(),
        "origin": origin,
        "process": process,
        "roast_level": roast,
        "format": fmt,
        "weight_g": weight,
        "price_toman": price,
        "price_per_100g": round(price / (weight / 100), 0) if price and weight else None,
        "specialty_score": None,
        "in_stock": in_stock,
        "image_url": image_url,
        "product_url": item.get("permalink"),
        "categories": "; ".join(cats),
        "description": re.sub(r"<[^>]+>", " ", desc + " " + short).strip()[:400],
    }


# ---------------------------------------------------------------------------
# WooCommerce wp/v2 (no price) strategy — Lamiz
# ---------------------------------------------------------------------------
def fetch_woo_v2(client, base):
    items, page = [], 1
    while True:
        r = client.get(f"{base}/wp-json/wp/v2/product", params={"per_page": 100, "page": page, "_embed": ""})
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)
        total = int(r.headers.get("x-wp-total", "0"))
        if len(items) >= total:
            break
        page += 1
        time.sleep(0.15)
    return items


def parse_woo_v2_item(item, roaster):
    title = (item.get("title") or {}).get("rendered", "") or ""
    content = (item.get("content") or {}).get("rendered", "") or ""
    excerpt = (item.get("excerpt") or {}).get("rendered", "") or ""
    # Taxonomy term IDs need names; the v2 response only gives ids here, so
    # fall back to slug text for classification.
    name = re.sub(r"<[^>]+>", "", title).strip()
    text = " ".join([name, re.sub(r"<[^>]+>", " ", content), re.sub(r"<[^>]+>", " ", excerpt)])
    weight = extract_weight_g(name, text)
    image_url = None
    try:
        image_url = item.get("_embedded", {}).get("wp:featuredmedia", [{}])[0].get("source_url")
    except (IndexError, KeyError, TypeError, AttributeError):
        pass
    return {
        "roaster": roaster,
        "product_name": name,
        "origin": extract_origin(text),
        "process": extract_process(text),
        "roast_level": extract_roast(text),
        "format": extract_format(text),
        "weight_g": weight,
        "price_toman": None,
        "price_per_100g": None,
        "specialty_score": None,
        "in_stock": None,
        "image_url": image_url,
        "product_url": item.get("link"),
        "categories": "",
        "description": re.sub(r"<[^>]+>", " ", content).strip()[:400],
    }


# ---------------------------------------------------------------------------
# Rio (Inertia JSON embedded per product page)
# ---------------------------------------------------------------------------
def fetch_rio(client, site):
    base = site["base"].rstrip("/")
    sitemap = client.get(f"{base}/products_sitemap_1.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap.text)
    out = []
    for u in urls:
        try:
            r = client.get(u)
            m = re.search(r'<script data-page="[^"]*" type="application/json">(.*?)</script>', r.text, re.S)
            if not m:
                continue
            import html as _html
            data = json.loads(_html.unescape(m.group(1)))
            model = data.get("props", {}).get("model", {})
            if not model:
                continue
            cats = model.get("categories", [])
            if isinstance(cats, str):
                cats = _safe_literal_list(cats)
            cat_names = [c.get("name", "") for c in cats if isinstance(c, dict)]
            name = model.get("name") or ""
            weight = extract_weight_g(model.get("weight"), name)
            price = parse_price(model.get("regular_price"))
            status = model.get("status_label", "")
            image_url = model.get("image") or ((model.get("images") or [None])[0])
            # fallback: medias[0].disk + file_name (Rio Inertia pattern)
            if not image_url:
                medias = model.get("medias")
                if isinstance(medias, list) and medias:
                    m0 = medias[0]
                    if isinstance(m0, dict):
                        disk = m0.get("disk", "")
                        fname = m0.get("file_name", "")
                        if disk and fname:
                            image_url = f"{base}/storage/{disk}{fname}"
            out.append({
                "roaster": site["roaster"],
                "product_name": name,
                "origin": extract_origin(name, *cat_names),
                "process": extract_process(name, model.get("description") or ""),
                "roast_level": extract_roast(name, *cat_names),
                "format": extract_format(name, *cat_names),
                "weight_g": weight,
                "price_toman": price,
                "price_per_100g": round(price / (weight / 100), 0) if price and weight else None,
                "specialty_score": None,
                "in_stock": status == "موجود",
                "image_url": image_url,
                "product_url": u,
                "categories": "; ".join(cat_names),
                "description": "",
            })
        except Exception:
            continue
        time.sleep(0.1)
    return out


def _safe_literal_list(s):
    try:
        return eval(s)  # rio embeds python-style list literals in the JSON string
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Lemm (custom .html pages)
# ---------------------------------------------------------------------------
def fetch_lemm(client, site):
    base = site["base"].rstrip("/")
    sm = client.get(f"{base}/sitemap.xml")
    urls = [u for u in re.findall(r"<loc>([^<]+)</loc>", sm.text) if re.search(r"/P\d+", u)]
    out = []
    for u in urls:
        try:
            r = client.get(u)
            h = r.text
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
            name = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else ""
            # price: Persian digits before تومان
            price_m = re.search(r"([۰-۹][۰-۹,٬]*)\s*تومان", h)
            price = parse_price(price_m.group(1)) if price_m else None
            weight = extract_weight_g(name)
            img_m = re.search(r'<img[^>]+src="([^"]+)"', h)
            image_url = urljoin(u, img_m.group(1)) if img_m else None
            out.append({
                "roaster": site["roaster"],
                "product_name": name,
                "origin": extract_origin(name),
                "process": extract_process(name),
                "roast_level": extract_roast(name),
                "format": extract_format(name),
                "weight_g": weight,
                "price_toman": price,
                "price_per_100g": round(price / (weight / 100), 0) if price and weight else None,
                "specialty_score": None,
                "in_stock": None,
                "image_url": image_url,
                "product_url": u,
                "categories": "",
                "description": "",
            })
        except Exception:
            continue
        time.sleep(0.1)
    return out


# ---------------------------------------------------------------------------
# Sam (Next.js __NEXT_DATA__)
# ---------------------------------------------------------------------------
def fetch_sam(client, site):
    base = site["base"].rstrip("/")
    r = client.get(f"{base}/products")
    slugs = sorted(set(re.findall(r'href=["\'](/products/[a-z0-9-]+)["\']', r.text)))
    out = []
    for slug in slugs:
        try:
            r = client.get(urljoin(base, slug))
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
            if not m:
                continue
            data = json.loads(m.group(1))
            prod = ((data.get("props") or {}).get("pageProps") or {}).get("data", {}).get("product", {})
            if not prod:
                continue
            name = prod.get("title") or ""
            price = parse_price(prod.get("price"))
            desc = prod.get("description") or ""
            text = " ".join([name, re.sub(r"<[^>]+>", " ", desc)])
            weight = extract_weight_g(name, text)
            labeled = extract_labeled_fields(desc)
            # image: try common Next.js product data shapes
            image_url = prod.get("image") or prod.get("featured_image") or prod.get("thumbnail")
            if isinstance(image_url, dict):
                image_url = image_url.get("src") or image_url.get("url")
            # fallback: gallery[0].url (Sam Coffee pattern)
            if not image_url:
                gallery = prod.get("gallery")
                if isinstance(gallery, list) and gallery:
                    image_url = gallery[0].get("url") if isinstance(gallery[0], dict) else None
            out.append({
                "roaster": site["roaster"],
                "product_name": name,
                "origin": labeled.get("origin") or extract_origin(name),
                "process": labeled.get("process") or extract_process(name),
                "roast_level": labeled.get("roast") or extract_roast(name),
                "format": extract_format(name),
                "weight_g": weight,
                "price_toman": price,
                "price_per_100g": round(price / (weight / 100), 0) if price and weight else None,
                "specialty_score": labeled.get("score"),
                "in_stock": bool(prod.get("available")),
                "image_url": image_url if isinstance(image_url, str) else None,
                "product_url": urljoin(base, slug),
                "categories": "",
                "description": re.sub(r"<[^>]+>", " ", desc).strip()[:400],
            })
        except Exception:
            continue
        time.sleep(0.1)
    return out


# ---------------------------------------------------------------------------
# TDS (Next.js + JSON-LD structured data)
# ---------------------------------------------------------------------------
def fetch_tds(client, site):
    base = site["base"].rstrip("/")
    r = client.get(f"{base}/products")
    slugs = sorted(set(re.findall(r'href=["\'](/products/[a-z0-9-]+)["\']', r.text)))
    out = []
    for slug in slugs:
        try:
            r = client.get(urljoin(base, slug))
            m = re.search(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S)
            if not m:
                continue
            ld = json.loads(m.group(1))
            name = ld.get("name") or ""
            desc = ld.get("description") or ""
            price = parse_price(int(ld["offers"]["price"])) if "offers" in ld and ld["offers"].get("price") else None
            in_stock = ld.get("offers", {}).get("availability") == "https://schema.org/InStock"
            img = ld.get("image") or ""
            image_url = urljoin(base, img) if img and not img.startswith("http") else (img or None)
            # Process from additionalProperty
            props = ld.get("additionalProperty") or []
            process = None
            variety = ""
            for p in props:
                pn = (p.get("name") or "").lower()
                pv = p.get("value") or ""
                if pn == "process":
                    process = extract_process(pv)
                elif pn == "variety":
                    variety = pv
            text = " ".join([name, desc, variety])
            weight = extract_weight_g(name, text)
            origin = extract_origin(name, desc, variety, ld.get("category") or "")
            out.append({
                "roaster": site["roaster"],
                "product_name": name.strip(),
                "origin": origin,
                "process": process or extract_process(name, desc),
                "roast_level": extract_roast(name, desc),
                "format": extract_format(name, desc),
                "weight_g": weight,
                "price_toman": price,
                "price_per_100g": round(price / (weight / 100), 0) if price and weight else None,
                "specialty_score": None,
                "in_stock": in_stock,
                "image_url": image_url,
                "product_url": urljoin(base, slug),
                "categories": "",
                "description": desc[:400],
            })
        except Exception:
            continue
        time.sleep(0.1)
    return out


def main():
    results = []
    client = httpx.Client(timeout=30, follow_redirects=True, headers=UA)
    for site in SITES:
        t = site["type"]
        print(f"[{site['roaster']}] fetching ({t}) ...", file=sys.stderr)
        try:
            if t == "woo":
                items = fetch_woo(client, site)
                parsed = [parse_woo_item(i, site["roaster"]) for i in items]
            elif t == "woo-old":
                items = fetch_woo(client, site, endpoint="/wp-json/wc/store/products")
                parsed = [parse_woo_item(i, site["roaster"]) for i in items]
            elif t == "woo-v2only":
                items = fetch_woo_v2(client, site["base"].rstrip("/"))
                parsed = [parse_woo_v2_item(i, site["roaster"]) for i in items]
            elif t == "rio":
                parsed = fetch_rio(client, site)
            elif t == "lemm":
                parsed = fetch_lemm(client, site)
            elif t == "sam":
                parsed = fetch_sam(client, site)
            elif t == "tds":
                parsed = fetch_tds(client, site)
            else:
                parsed = []
            results.extend(parsed)
            print(f"   -> {len(parsed)} items", file=sys.stderr)
        except Exception as e:
            print(f"   !! error: {e}", file=sys.stderr)
        time.sleep(0.3)

    with open(OUT, "w") as f:
        for rec in results:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(results)} records to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
