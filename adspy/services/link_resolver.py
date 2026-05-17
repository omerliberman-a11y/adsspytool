"""Link resolver — follows redirects from a CTA/landing URL through to the final
destination, capturing each hop. Detects affiliate networks along the way.

Strategy:
  1. Try HTTP redirect walking with httpx (cheap, fast — handles 301/302/307/308).
  2. If the final HTML contains a meta-refresh or JS-redirect signal, escalate to
     Playwright to follow it.
  3. Stop on max hops or when domain stops changing.

Affiliate networks detected:
  ClickBank, Digistore24, MaxBounty, BuyGoods, WarriorPlus, JVZoo, CJ Affiliate,
  ShareASale, Awin, Impact, Refersion.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.utils.logging import get_logger

log = get_logger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
MAX_HOPS = 12
PER_REQUEST_TIMEOUT = 12

# domain pattern → affiliate-network tag
AFFILIATE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhop\.clickbank\.net\b", re.I), "clickbank"),
    (re.compile(r"\bclickbank\.com\b", re.I), "clickbank"),
    (re.compile(r"\bdigistore24\.com\b", re.I), "digistore24"),
    (re.compile(r"\bmaxbounty\.com\b", re.I), "maxbounty"),
    (re.compile(r"\bmb01\.com\b", re.I), "maxbounty"),
    (re.compile(r"\bbuygoods\.com\b", re.I), "buygoods"),
    (re.compile(r"\bwarriorplus\.com\b", re.I), "warriorplus"),
    (re.compile(r"\bjvz\d?\.com\b", re.I), "jvzoo"),
    (re.compile(r"\bjvzoo\.com\b", re.I), "jvzoo"),
    (re.compile(r"\bcj\.com\b|\bdpbolvw\.net\b|\banrdoezrs\.net\b", re.I), "cj_affiliate"),
    (re.compile(r"\bshareasale\.com\b", re.I), "shareasale"),
    (re.compile(r"\bawin1\.com\b|\bawin\.com\b", re.I), "awin"),
    (re.compile(r"\bimpact\.com\b|\b7eer\.net\b", re.I), "impact"),
    (re.compile(r"\brefersion\.com\b|\brfsn\.com\b", re.I), "refersion"),
    (re.compile(r"\brakuten\.com\b|\blinksynergy\.com\b", re.I), "rakuten"),
    (re.compile(r"\bskimresources\.com\b|\bgo\.redirectingat\.com\b", re.I), "skimlinks"),
]

META_REFRESH_RE = re.compile(
    r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]+content=[\"']?[^\";']*url=([^\";'>\s]+)",
    re.I,
)


@dataclass
class LinkHop:
    index: int
    url: str
    host: str
    status: int | None  # None for JS-only hops
    kind: str  # http | meta_refresh | js
    affiliate: str | None = None


def _detect_affiliate(url: str) -> str | None:
    for pattern, tag in AFFILIATE_PATTERNS:
        if pattern.search(url):
            return tag
    return None


def _host(url: str) -> str:
    h = (urlparse(url).netloc or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return h


def _walk_http_redirects(url: str) -> tuple[list[LinkHop], str]:
    """Walk HTTP redirects without following them automatically. Returns (hops, final_html_or_empty)."""
    hops: list[LinkHop] = []
    seen: set[str] = set()
    current = url
    final_html = ""
    try:
        client = httpx.Client(
            headers={"User-Agent": UA}, follow_redirects=False, timeout=PER_REQUEST_TIMEOUT
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("link_resolver_client_init_failed", error=str(exc))
        return hops, final_html

    with client:
        for i in range(MAX_HOPS):
            if current in seen:
                break
            seen.add(current)
            try:
                r = client.get(current)
            except httpx.HTTPError as exc:
                hops.append(
                    LinkHop(
                        index=i,
                        url=current,
                        host=_host(current),
                        status=None,
                        kind="error",
                        affiliate=_detect_affiliate(current),
                    )
                )
                log.warning("link_resolver_http_failed", url=current, error=str(exc))
                break

            hops.append(
                LinkHop(
                    index=i,
                    url=current,
                    host=_host(current),
                    status=r.status_code,
                    kind="http",
                    affiliate=_detect_affiliate(current),
                )
            )

            if r.is_redirect:
                loc = r.headers.get("location")
                if not loc:
                    break
                current = str(httpx.URL(current).join(loc))
                continue

            # terminal — capture HTML for meta-refresh / JS-redirect detection
            content_type = r.headers.get("content-type", "")
            if "text/html" in content_type or "text/plain" in content_type:
                final_html = r.text[:200_000]
            break
    return hops, final_html


def _maybe_follow_meta_refresh(hops: list[LinkHop], final_html: str) -> list[LinkHop]:
    """Detect <meta http-equiv=refresh url=...> on the last page and follow once."""
    if not hops or not final_html:
        return hops
    last_url = hops[-1].url
    m = META_REFRESH_RE.search(final_html)
    if not m:
        return hops
    target = m.group(1).strip().strip("'\"")
    target_abs = str(httpx.URL(last_url).join(target))
    hops.append(
        LinkHop(
            index=len(hops),
            url=target_abs,
            host=_host(target_abs),
            status=None,
            kind="meta_refresh",
            affiliate=_detect_affiliate(target_abs),
        )
    )
    # Continue walking from the meta-refresh target via HTTP redirects.
    next_hops, _ = _walk_http_redirects(target_abs)
    # offset indices to be unique
    for h in next_hops[1:]:  # skip first; we already added it
        h.index = len(hops)
        hops.append(h)
    return hops


def resolve(url: str) -> tuple[list[LinkHop], str | None, str | None, str | None]:
    """Resolve a URL through redirects. Returns (hops, final_url, final_domain, affiliate)."""
    hops, final_html = _walk_http_redirects(url)
    hops = _maybe_follow_meta_refresh(hops, final_html)

    if not hops:
        return [], None, None, None

    final = hops[-1]
    final_url = final.url
    final_domain = final.host
    # Affiliate is "the strongest non-final hop" — the redirector domain, not the
    # landing page. If only the final hop is an affiliate, use that.
    affiliate = next(
        (h.affiliate for h in hops if h.affiliate and h is not final),
        final.affiliate,
    )
    return hops, final_url, final_domain, affiliate


def resolve_for_ad(platform: str, ad_id: str) -> dict[str, Any] | None:
    """Resolve cta_url for an ad and persist the result. Returns the dict written."""
    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            return None
        target = ad.cta_url or ad.landing_url
        # Skip ad-library URLs — they're already the source_url, not a destination.
        if target and ("facebook.com/ads/library" in target or "library.tiktok.com" in target):
            target = None
        if not target:
            log.info("link_resolver_skip_no_target", platform=platform, ad_id=ad_id)
            return None

    hops, final_url, final_domain, affiliate = resolve(target)
    chain = [asdict(h) for h in hops]

    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            return None
        ad.link_chain = chain
        ad.final_url = final_url
        ad.final_domain = final_domain
        ad.affiliate_network = affiliate
        ad.link_resolved_at = datetime.now(UTC)

    log.info(
        "link_resolved",
        platform=platform,
        ad_id=ad_id,
        hops=len(chain),
        final_domain=final_domain,
        affiliate=affiliate,
    )
    return {
        "hops": chain,
        "final_url": final_url,
        "final_domain": final_domain,
        "affiliate_network": affiliate,
    }
