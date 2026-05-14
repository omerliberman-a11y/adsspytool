"""Competitor enrichment + scan.

`enrich_competitor`: fetch homepage, extract social handles + tech-stack fingerprint,
resolve the Facebook page numeric id (Playwright fallback when needed).

`scan_competitor`: use fb_page_id to hit Meta Graph /ads_archive, ingest ads with
the competitor_id stamped on each row.

`link_existing_ads_to_competitor`: backfill the competitor_id on previously-ingested
ads that match this competitor's fb_page_id or domain.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from adspy.analyzers.scoring import score_ad_row
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.competitor import Competitor
from adspy.normalize import normalize_meta_ad
from adspy.utils.errors import ScrapeError
from adspy.utils.logging import get_logger

log = get_logger(__name__)

# --- enrichment helpers -------------------------------------------------------

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# script src / dom signature → tech_stack tag
TECH_SIGNATURES: dict[str, str] = {
    "cdn.shopify.com": "shopify",
    "shopify.com/s/files": "shopify",
    "checkout.shopify.com": "shopify",
    "klaviyo.com/onsite": "klaviyo",
    "static.klaviyo.com": "klaviyo",
    "clickfunnels.com": "clickfunnels",
    "cf-static.clickfunnels": "clickfunnels",
    "kajabi.com": "kajabi",
    "kajabi-storefronts": "kajabi",
    "convertkit.com": "convertkit",
    "ck.page": "convertkit",
    "activecampaign.com": "activecampaign",
    "hubspot.com": "hubspot",
    "hs-scripts.com": "hubspot",
    "gohighlevel": "gohighlevel",
    "leadpages.net": "leadpages",
    "unbounce.com": "unbounce",
    "instapage.com": "instapage",
    "googletagmanager.com": "gtm",
    "google-analytics.com": "google_analytics",
    "googleadservices.com": "google_ads",
    "googletagservices.com": "google_ads",
    "connect.facebook.net/en_US/fbevents.js": "meta_pixel",
    "static.ads-twitter.com": "twitter_pixel",
    "analytics.tiktok.com": "tiktok_pixel",
    "pinterest.com/v3/?event=init": "pinterest_pixel",
    "snap.licdn.com/li.lms-analytics": "linkedin_pixel",
    "stripe.com/v3": "stripe",
    "checkout.stripe.com": "stripe",
    "buy.stripe.com": "stripe",
    "paypal.com/sdk": "paypal",
    "shopify.com/payments": "shopify_payments",
    "recharge": "recharge_subscriptions",
}

# pixel-id regex per provider (capture the id)
PIXEL_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    ("meta_pixel", re.compile(r"fbq\(['\"]init['\"],\s*['\"](\d{12,18})['\"]")),
    ("google_ads", re.compile(r"AW-(\d+)")),
    ("google_analytics", re.compile(r"G-([A-Z0-9]{6,12})")),
    ("tiktok_pixel", re.compile(r"ttq\.load\(['\"]([A-Z0-9]{18,24})['\"]")),
]


def _normalize_domain(raw: str) -> str:
    s = raw.strip().lower()
    if "://" not in s:
        s = "https://" + s
    parsed = urlparse(s)
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host


def _root_url(domain: str) -> str:
    return f"https://{domain}"


def _fetch_homepage(domain: str) -> str:
    url = _root_url(domain)
    with httpx.Client(
        headers={"User-Agent": UA}, follow_redirects=True, timeout=15
    ) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def _extract_social_handles(html: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {
        "fb_page_url": None,
        "instagram_handle": None,
        "tiktok_handle": None,
        "twitter_handle": None,
        "youtube_channel": None,
        "linkedin_company": None,
    }
    # facebook — accept facebook.com/<slug> or facebook.com/pages/<slug>/<id>
    m = re.search(
        r'https?://(?:www\.|m\.|business\.)?facebook\.com/(?!sharer|share|tr\?|plugins|dialog)([^"\'\\\s<>?#]+)',
        html, re.IGNORECASE,
    )
    if m:
        slug = m.group(1).split("?")[0].rstrip("/")
        out["fb_page_url"] = f"https://www.facebook.com/{slug}"

    m = re.search(
        r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)', html, re.IGNORECASE
    )
    if m:
        out["instagram_handle"] = m.group(1).rstrip("/")

    m = re.search(
        r'https?://(?:www\.)?tiktok\.com/@([A-Za-z0-9_.]+)', html, re.IGNORECASE
    )
    if m:
        out["tiktok_handle"] = m.group(1).rstrip("/")

    m = re.search(
        r'https?://(?:www\.)?(?:twitter|x)\.com/([A-Za-z0-9_]+)', html, re.IGNORECASE
    )
    if m:
        handle = m.group(1).rstrip("/")
        if handle.lower() not in ("share", "intent", "home"):
            out["twitter_handle"] = handle

    m = re.search(
        r'https?://(?:www\.)?youtube\.com/(?:channel/|@)([A-Za-z0-9_\-]+)', html
    )
    if m:
        out["youtube_channel"] = m.group(1).rstrip("/")

    m = re.search(
        r'https?://(?:www\.)?linkedin\.com/company/([A-Za-z0-9_\-]+)', html
    )
    if m:
        out["linkedin_company"] = m.group(1).rstrip("/")

    return out


def _detect_tech_stack(html: str) -> tuple[list[str], list[str]]:
    found: set[str] = set()
    low = html.lower()
    for signature, tag in TECH_SIGNATURES.items():
        if signature.lower() in low:
            found.add(tag)

    pixels: list[str] = []
    for tag, regex in PIXEL_REGEXES:
        for match in regex.finditer(html):
            pixels.append(f"{tag}:{match.group(1)}")
            found.add(tag)
    # dedupe pixels
    pixels = list(dict.fromkeys(pixels))
    return sorted(found), pixels


def _resolve_fb_page_id(fb_page_url: str) -> str | None:
    """Resolve a facebook.com/<slug> URL to a numeric page_id.

    Patterns ordered most-specific → broadest. The `fb://profile/<id>` deep-link
    embedded in Open Graph meta tags is the most reliable signal.
    """
    patterns = (
        r'fb://(?:page|profile)/(\d{6,20})',
        r'"userID"\s*:\s*"(\d{6,20})"',
        r'"pageID"\s*:\s*"(\d{6,20})"',
        r'"page_id"\s*:\s*"(\d{6,20})"',
        r'"entity_id"\s*:\s*"(\d{6,20})"',
        r'"profile_id"\s*:\s*"?(\d{6,20})"?',
        r'profile_owner=(\d{6,20})',
        r'pages/[^/]+/(\d{6,20})',
    )

    def _match(text: str) -> str | None:
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                return m.group(1)
        return None

    # Cheap pass — plain HTML fetch.
    try:
        with httpx.Client(
            headers={"User-Agent": UA}, follow_redirects=True, timeout=20
        ) as client:
            r = client.get(fb_page_url)
            hit = _match(r.text)
            if hit:
                return hit
    except httpx.HTTPError as exc:
        log.warning("fb_page_id_http_fetch_failed", error=str(exc))

    # Playwright fallback — FB renders much of the page via JS.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(user_agent=UA)
                page = ctx.new_page()
                page.goto(fb_page_url, wait_until="domcontentloaded", timeout=30000)
                return _match(page.content())
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("fb_page_id_playwright_failed", error=str(exc))
    return None


# --- public services ----------------------------------------------------------

def create_competitor(domain: str, *, name: str | None = None,
                       tags: list[str] | None = None) -> int:
    norm = _normalize_domain(domain)
    with session_scope() as s:
        existing = s.query(Competitor).filter_by(domain=norm).one_or_none()
        if existing:
            return existing.id
        c = Competitor(domain=norm, name=name, tags=tags or None)
        s.add(c)
        s.flush()
        return c.id


def enrich_competitor(competitor_id: int) -> None:
    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise ScrapeError(f"competitor {competitor_id} not found")
        domain = c.domain

    try:
        html = _fetch_homepage(domain)
    except httpx.HTTPError as exc:
        with session_scope() as s:
            c = s.get(Competitor, competitor_id)
            if c is not None:
                c.last_scan_error = f"homepage fetch failed: {exc}"
                c.last_enriched_at = datetime.now(UTC)
        log.error("enrich_homepage_fetch_failed", domain=domain, error=str(exc))
        return

    socials = _extract_social_handles(html)
    tech, pixels = _detect_tech_stack(html)
    fb_page_id: str | None = None
    if socials.get("fb_page_url"):
        fb_page_id = _resolve_fb_page_id(socials["fb_page_url"])

    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            return
        for k, v in socials.items():
            if v is not None:
                setattr(c, k, v)
        if fb_page_id:
            c.fb_page_id = fb_page_id
        c.tech_stack = tech or None
        c.pixels = pixels or None
        c.last_enriched_at = datetime.now(UTC)
        c.last_scan_error = None
    log.info(
        "competitor_enriched",
        competitor_id=competitor_id,
        domain=domain,
        fb_page_id=fb_page_id,
        tech=tech,
        socials={k: v for k, v in socials.items() if v},
    )


def scan_competitor(competitor_id: int, *, limit: int = 200) -> int:
    """Hit Meta Graph /ads_archive for this competitor's fb_page_id. Returns ads upserted."""
    from sqlalchemy.dialects.postgresql import insert

    from adspy.scrapers.base import ScrapeQuery
    from adspy.scrapers.meta import MetaScraper

    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is None:
            raise ScrapeError(f"competitor {competitor_id} not found")
        if not c.fb_page_id:
            raise ScrapeError(
                f"competitor {competitor_id} has no fb_page_id — run enrichment first"
            )
        page_id = c.fb_page_id

    query = ScrapeQuery(advertiser_page=page_id, limit=limit)
    rows: list[dict[str, Any]] = []
    for raw in MetaScraper().scrape(query):
        try:
            ad = normalize_meta_ad(raw)
        except Exception as exc:  # noqa: BLE001
            log.warning("competitor_scan_normalize_failed", error=str(exc))
            continue
        ad["winner_score"] = score_ad_row(ad)
        ad["competitor_id"] = competitor_id
        ad["updated_at"] = datetime.now(UTC)
        rows.append(ad)

    if rows:
        with session_scope() as s:
            stmt = insert(Ad).values(rows)
            update_cols = {
                col.name: getattr(stmt.excluded, col.name)
                for col in Ad.__table__.columns
                if col.name not in ("platform", "ad_id", "created_at")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=["platform", "ad_id"], set_=update_cols
            )
            s.execute(stmt)

    with session_scope() as s:
        c = s.get(Competitor, competitor_id)
        if c is not None:
            c.last_scanned_at = datetime.now(UTC)
            c.last_scan_error = None

    log.info("competitor_scan_done", competitor_id=competitor_id, upserted=len(rows))
    return len(rows)


def auto_link_ad_to_competitor(ad: dict[str, Any]) -> int | None:
    """Return competitor_id if this ad matches a tracked competitor (by FB page_id or domain in landing_url)."""
    candidate_page_id = ad.get("advertiser_page_id")
    landing = ad.get("landing_url") or ad.get("cta_url")
    if not candidate_page_id and not landing:
        return None

    with session_scope() as s:
        if candidate_page_id:
            c = s.query(Competitor).filter_by(fb_page_id=str(candidate_page_id)).one_or_none()
            if c is not None:
                return c.id
        if landing:
            host = urlparse(landing).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if host:
                c = s.query(Competitor).filter_by(domain=host).one_or_none()
                if c is not None:
                    return c.id
    return None
