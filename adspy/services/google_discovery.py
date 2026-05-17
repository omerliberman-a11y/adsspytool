"""Google Ads Transparency — advertiser discovery via SearchSuggestions RPC.

The full ad-creative RPC (SearchService/SearchCreatives) requires reverse-
engineering Google's protobuf-style positional encoding for varied query
shapes and is brittle. SearchSuggestions on the other hand is a simple,
stable POST that returns a structured list of advertisers per keyword.

We use it as a competitor-discovery feed: given a keyword, surface all
advertisers running ads under that term across regions, with their estimated
ad-count tier. Each advertiser becomes a row in `competitors` (auto-named),
which then feeds the existing Competitor pipeline (enrich → scan).

Endpoint:
  POST https://adstransparency.google.com/anji/_/rpc/SearchService/SearchSuggestions
  Body: f.req=<URL-encoded JSON>
  JSON: {"1": keyword, "2": page_size, "3": offset_or_limit, "5": {"1": region_id}}
  Region id: 1 = anywhere (returns mixed countries per advertiser).

Response shape (positional protobuf-as-JSON):
  {"1": [
    {"1": {
       "1": advertiser_name,
       "2": advertiser_id (AR...),
       "3": country_code,
       "4": {"2": {"1": low_ad_count, "2": high_ad_count}},
       "5": optional bool (suggested?)
    }},
    ...
  ]}
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx

from adspy.db.session import session_scope
from adspy.models.competitor import Competitor
from adspy.utils.logging import get_logger

log = get_logger(__name__)

ENDPOINT = "https://adstransparency.google.com/anji/_/rpc/SearchService/SearchSuggestions"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": UA,
    "X-Same-Domain": "1",
    "Referer": "https://adstransparency.google.com/",
}


@dataclass
class GoogleAdvertiser:
    name: str
    advertiser_id: str
    country: str | None
    ad_count_low: int | None
    ad_count_high: int | None


def search_suggestions(
    keyword: str, *, limit: int = 20, region: int = 1
) -> list[GoogleAdvertiser]:
    """Return advertisers matching the keyword. `region=1` = anywhere."""
    body = json.dumps(
        {"1": keyword, "2": limit, "3": limit, "5": {"1": region}}
    )
    data = ("f.req=" + urllib.parse.quote(body)).encode()
    with httpx.Client(timeout=20) as client:
        r = client.post(ENDPOINT, content=data, headers=HEADERS)
        r.raise_for_status()
        payload = r.json()
    return _parse_suggestions(payload)


def _parse_suggestions(payload: dict[str, Any]) -> list[GoogleAdvertiser]:
    out: list[GoogleAdvertiser] = []
    rows = payload.get("1") or []
    for row in rows:
        inner = row.get("1") if isinstance(row, dict) else None
        if not isinstance(inner, dict):
            continue
        name = inner.get("1")
        adv_id = inner.get("2")
        country = inner.get("3")
        counts = inner.get("4", {}).get("2") if isinstance(inner.get("4"), dict) else None
        lo = hi = None
        if isinstance(counts, dict):
            lo = _as_int(counts.get("1"))
            hi = _as_int(counts.get("2"))
        if name and adv_id:
            out.append(
                GoogleAdvertiser(
                    name=str(name),
                    advertiser_id=str(adv_id),
                    country=str(country) if country else None,
                    ad_count_low=lo,
                    ad_count_high=hi,
                )
            )
    return out


def _as_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def discover_into_competitors(
    keyword: str,
    *,
    limit: int = 20,
    region: int = 1,
    min_ad_count: int = 5,
    domain_template: str | None = None,
) -> int:
    """Convert Google AT suggestions into Competitor rows. Returns new rows added.

    Since Google AT exposes advertiser names but not their primary domains, we
    synthesize a placeholder domain `<slug>.google-at` for tracking purposes.
    The Competitor enrichment phase can later attempt to resolve the real domain
    via web-search if/when we add that capability.

    Filter: skip advertisers below `min_ad_count` (high-bound) to ignore noise.
    """
    adv = search_suggestions(keyword, limit=limit, region=region)
    added = 0
    with session_scope() as s:
        for a in adv:
            if a.ad_count_high is not None and a.ad_count_high < min_ad_count:
                continue
            slug = _slugify(a.name)
            domain = (
                domain_template.format(slug=slug) if domain_template else f"{slug}.google-at"
            )
            existing = s.query(Competitor).filter_by(domain=domain).one_or_none()
            if existing:
                continue
            c = Competitor(
                domain=domain,
                name=a.name,
                tags=["google-at", f"discovered:{keyword}"],
                notes=(
                    f"Discovered via Google Ads Transparency keyword '{keyword}'. "
                    f"Google advertiser_id={a.advertiser_id}, country={a.country}, "
                    f"~{a.ad_count_low}-{a.ad_count_high} ads."
                ),
            )
            s.add(c)
            added += 1
    log.info("google_at_discovery_done", keyword=keyword, found=len(adv), added=added)
    return added


def _slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name.strip().lower()).strip("-")
    return s[:60] or "unknown"
