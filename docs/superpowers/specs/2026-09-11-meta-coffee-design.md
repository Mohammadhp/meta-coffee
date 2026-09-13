# Meta-Coffee — Design Spec

*Date: 2026-09-11 · Status: Draft for review*

## 1. Vision & Problem

Iran's specialty-coffee market is growing fast among home enthusiasts, but supply is
fragmented across dozens of small roasters, shops, and importers — each carrying a
handful of SKUs, using inconsistent naming, and often publishing no structured catalog
at all. A home enthusiast who wants "a good Brazilian with chocolate notes" or "a
replacement gasket for my grinder" has no single place to search.

**Meta-Coffee is a vertical search & discovery engine for coffee** — a Torob-style
aggregator, but built for *discovery* (by origin, roast, flavor, brew method), not just
price comparison of a product the user already knows.

**It is not a marketplace.** No checkout, no inventory, no fulfillment. Every result
links out to the seller's own page.

## 2. Strategic Approach

**A + C hybrid: scrape where trust is cheap, curate where it matters.**

- **Beans** — small catalog, high trust bar. Hand-curated via Django admin with a
  controlled vocabulary and a per-listing freshness stamp. No scraper needed at v1.
- **Gear / equipment / parts** — large catalog, no freshness sensitivity. Scraped from
  web shops (strictly **no Instagram scraping**), with polite rate-limiting and a
  `last_crawled` stamp.

**Bullseye customer (v1):** home enthusiasts.
**Wedge (v1):** beans (origin / roast / flavor notes) + brewing gear.

The edge over Torob/Digikala is **discovery + trust**, not price: a verified, freshness-
stamped catalog that a generalist can't cheaply copy.

## 3. Scope (v1)

**In scope**

- Search + filters over two catalogs: beans and gear.
- Thin editorial layer (~5–10 Persian reviews / buying guides).
- Outbound "where to buy" links carrying UTM parameters.
- Zero-result query log (records every search that returns nothing).
- Freshness signals (`last_verified` / `last_crawled`) surfaced to users.

**Out of scope (explicit deferrals)**

- Checkout / cart / payments, user accounts, seller billing/subscription system.
- Instagram *scraping* (Instagram as a **content channel** is in scope).
- Industrial / B2B catalog, mobile apps, recommendation ML.

## 4. Data Model

Three core entities. Every listing points to a **Seller** and carries enough structure
to power real filters, not just a keyword box.

**Seller**

- `name`, `type` (`roaster` | `shop` | `importer`), `city`, `site_url`, `instagram`
- `relationship` = `indexed` | `partner`
  - This single field is the CRM: the list of people to eventually walk up to and charge.

**BeanListing**

- `origin` (country + optional region), `variety`, `process`, `roast_level`,
  `flavor_notes`, `roasted_on`, `price`, `price_per_kg`, `in_stock`, `last_verified`,
  `seller_id`, `link`
- Controlled vocabulary for `origin` / `process` / `roast_level`; free text for notes.
- Missing fields are tolerated but visible — search can filter "only beans with `process`
  filled".

**GearListing**

- `category` (`grinder` | `brewer` | `kettle` | `filter` | `accessory`), `brand`,
  `model`, `key_specs` (burr size, brew method, capacity — best-effort), `price`,
  `in_stock`, `last_crawled`, `seller_id`, `link`

**Staleness mechanism:** `last_verified` (beans) and `last_crawled` (gear) are surfaced
to users as "verified N days ago" and drive internal re-verification / re-crawl cadence.

## 5. Product: Search & Discovery

- **Structured facets do the heavy lifting** (exact match on controlled vocab): origin,
  roast, process, price range, category.
- **Free-text via `pg_trgm`** (trigram matching) for flavor notes and names — handles
  Persian/English mixing without heavyweight full-text search.
- Freshness confidence is visible and sortable.
- Zero-result query log becomes the product roadmap *and* the seller pitch data.

## 6. Content & Distribution

One content engine, two channels:

- **Blog (SEO + conversion, Persian):** guides and reviews targeting real search demand
  (e.g. "بهترین آسیاب قهوه زیر ۱۰ میلیون"). Every post links internally to a real
  listing or seller page — content exists to feed the search engine, never floats free
  of the catalog.
- **Instagram (awareness + trust):** reels, carousels, bean spotlights. Link-in-bio →
  site. Earns the recognition that makes users later search the web and find Meta-Coffee.

Pre-launch backlog of ~10–15 pieces so the site doesn't look empty on day one.

## 7. Technical Architecture & Stack

Stack is **Python-first** (no JS/TS expertise on team):

- **Django + PostgreSQL** — ORM, server-rendered RTL templates (no JS required),
  `pg_trgm` for search.
- **Django Admin = the bean curation interface.** The hand-curated bean workflow
  (enter/edit listings, controlled-vocab choices, per-seller verify checklist) is the
  Django admin use case. No custom admin UI needed at v1.
- **Scraper in Python** — `httpx` + `BeautifulSoup` (or `selectolax`), run as a Django
  management command on cron. Website-only, respects `robots.txt`, rate-limited.
  - **Rule:** if a page stops parsing, mark `in_stock = false` and alert — never keep
    stale stock listed silently.
- **Hosting:** offshore origin + `.com`, fronted by an Iran-friendly CDN (e.g. ArvanCloud)
  for reachability and speed inside Iran.
- **Search reality:** users will mix Persian and English ("قهوه برزیل" / "Brazil Santos" /
  "Gesha").

Deliberately absent in v1: Elasticsearch, microservices, ML, queue workers, mobile apps.

## 8. Seller & Monetization Roadmap

- **Phase 0 (v1):** index freely, make no money. Every seller is `indexed`.
- **Phase 1:** once UTM data shows referral value, approach benefiting roasters → promote
  to `partner` (claimed profile, better placement). Revenue *can* start here.
- **Phase 2:** sponsored search slots + featured placement (gear shops especially);
  possible affiliate/CPA if a seller network materializes.

Pitch data = zero-result log + outbound click stats ("your beans got 300 clicks last
month → featured placement = X/month").

**Guardrail:** disclose sponsored placement ("اسپانسری"). Never hide it — trust is the
moat.

## 9. Success Metrics

**v1 "good enough to go all-in":**

1. A home enthusiast types "brazilian, chocolate, medium roast" → gets 3+ real, in-stock
   results on the first try.
2. Every bean listing carries a `last_verified` stamp; no dead stock lingers.
3. Sellers see measurable referral traffic (UTM).
4. A few editorial pages start ranking / pulling enthusiasts organically.

**North star:** share of Iran's coffee-intent search queries that resolve at Meta-Coffee.

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Catalog goes stale → trust loss | Freshness stamps; eager `in_stock=false` on parse failure |
| Scraping breaks / gets blocked | Polite crawl, `robots.txt`, alert on parse failure |
| Torob/Digikala copies the vertical | Defensibility = curated freshness + trust + community, not the search box |
| Monetization deferred → cash gap | Capital already available; Phase 1 trigger is data-driven |
| RTL / Persian search quality | Controlled vocab carries structure; `pg_trgm` covers free text |
| Offshore reachability inside Iran | Iran-friendly CDN in front of origin |

## 11. Open Questions (parked — decide later)

- Product / brand name.
- Seller payment integration specifics (Phase 2).
- Affiliate vs subscription pricing model (Phase 2).