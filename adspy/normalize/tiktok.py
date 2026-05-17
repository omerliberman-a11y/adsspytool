"""Normalizer for TikTok Creative Center materials into the unified Ad schema."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from adspy.utils.errors import NormalizerError

# Map TikTok `like` count → coarse reach band (proxy: high likes ≈ wide reach).
LIKE_TO_REACH_BAND = [
    (1_000_000, ">1000000"),
    (500_000, "500000-1000000"),
    (100_000, "100000-500000"),
    (50_000, "50000-100000"),
    (10_000, "10000-50000"),
    (5_000, "5000-10000"),
    (1_000, "1000-5000"),
]


def _reach_band_from_likes(like: int | None) -> str | None:
    if like is None or like <= 0:
        return None
    for threshold, band in LIKE_TO_REACH_BAND:
        if like >= threshold:
            return band
    return "<1000"


def normalize_tiktok_ad(raw: dict[str, Any]) -> dict[str, Any]:
    ad_id = raw.get("id")
    if not ad_id:
        raise NormalizerError("TikTok record missing 'id'")

    video_info = raw.get("video_info") or {}
    video_url_map = video_info.get("video_url") or {}
    cover = video_info.get("cover")

    media_urls: list[str] = []
    if cover:
        media_urls.append(str(cover))
    # Prefer 720p, fall back to 540p
    for quality in ("720p", "540p", "1080p"):
        url = video_url_map.get(quality)
        if url:
            media_urls.append(str(url))
            break

    period_days = int(raw.get("_scraped_period_days") or 30)
    country = str(raw.get("_scraped_country") or "US")
    last_seen = datetime.now(UTC)
    first_seen = last_seen - timedelta(days=period_days)

    like = raw.get("like")
    brand = raw.get("brand_name")
    if not brand:
        # Fall back to first @mention in the title — often the advertiser handle.
        # Use Unicode word class so accented brand names (e.g. @Nécessaire) work.
        import re as _re
        title = raw.get("ad_title") or ""
        m = _re.search(r"@([\w&.\-]+)", title, flags=_re.UNICODE)
        if m:
            brand = f"@{m.group(1).strip('.-')}"
        else:
            brand = "TikTok advertiser"

    return {
        "platform": "tiktok",
        "ad_id": str(ad_id),
        "advertiser_name": brand,
        "advertiser_page_id": None,
        "advertiser_url": None,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "days_active": period_days,  # ad was active within the scraped window
        "countries": [country],
        "languages": None,
        "placements": ["tiktok"],
        "creative_type": "video",
        "media_urls": media_urls or None,
        "headline": (raw.get("ad_title") or "")[:200] or None,
        "primary_text": raw.get("ad_title") or None,
        "description": None,
        "cta_text": None,
        "cta_url": None,
        "landing_url": None,
        "variant_count": 1,
        "reach_band": _reach_band_from_likes(like) if isinstance(like, int) else None,
        "impressions_band": None,
        "spend_band": str(raw.get("cost")) if raw.get("cost") is not None else None,
        "raw_json": raw,
    }
