from datetime import UTC, datetime
from typing import Any

from dateutil import parser as dateparser

from adspy.utils.errors import NormalizerError


def _first(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(int(value), tz=UTC)
    if isinstance(value, str):
        try:
            dt = dateparser.parse(value)
        except (ValueError, TypeError):
            return None
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    return None


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [str(v)]


def _detect_creative_type(raw: dict[str, Any]) -> str:
    if _first(raw, "videoHdUrl", "video_hd_url", "videoUrl", "video_sd_url"):
        return "video"
    cards = _first(raw, "cards") or _first(raw, "snapshot", "cards")
    if isinstance(cards, list) and len(cards) > 1:
        return "carousel"
    if _first(raw, "imageUrl", "image_url", "originalImageUrl"):
        return "image"
    if _first(raw, "body", "primaryText", "primary_text"):
        return "text"
    return "image"


def _extract_media(raw: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("videoHdUrl", "video_hd_url", "videoSdUrl", "video_sd_url"):
        v = raw.get(key)
        if v:
            urls.append(str(v))
    for key in ("imageUrl", "image_url", "originalImageUrl", "original_image_url"):
        v = raw.get(key)
        if v:
            urls.append(str(v))
    cards = raw.get("cards") or raw.get("snapshot", {}).get("cards") if isinstance(
        raw.get("snapshot"), dict
    ) else raw.get("cards")
    if isinstance(cards, list):
        for c in cards:
            if not isinstance(c, dict):
                continue
            for k in ("videoHdUrl", "originalImageUrl", "imageUrl"):
                v = c.get(k)
                if v:
                    urls.append(str(v))
    return urls


def normalize_meta_ad(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a single record from apify/facebook-ads-scraper into our unified ad schema.

    The actor's field names have drifted across versions, so we accept several casings.
    """
    ad_id = _first(raw, "adArchiveID", "ad_archive_id", "adId", "id")
    if not ad_id:
        raise NormalizerError("Meta record missing ad_archive_id / adId / id")

    snapshot = raw.get("snapshot") if isinstance(raw.get("snapshot"), dict) else {}
    page_name = _first(raw, "pageName", "page_name") or _first(snapshot, "pageName", "page_name")
    page_id = _first(raw, "pageID", "page_id") or _first(snapshot, "page_id", "pageID")

    first_seen = _parse_dt(
        _first(raw, "startDate", "start_date", "startDateString", "ad_creation_time")
    )
    last_seen = _parse_dt(_first(raw, "endDate", "end_date", "endDateString")) or datetime.now(UTC)
    days_active = (
        (last_seen - first_seen).days if first_seen and last_seen else None
    )

    countries = _as_list(_first(raw, "reachedCountries", "countries", "targetCountries"))
    languages = _as_list(_first(raw, "languages", "ad_creative_link_caption_languages"))
    placements = _as_list(_first(raw, "publisherPlatforms", "publisher_platforms"))

    headline = _first(raw, "title", "headline") or _first(snapshot, "title", "headline")
    body = _first(raw, "body", "primaryText", "primary_text") or _first(
        snapshot, "body", "primaryText"
    )
    description = _first(raw, "linkDescription", "link_description") or _first(
        snapshot, "linkDescription"
    )
    cta_text = _first(raw, "ctaText", "cta_text") or _first(snapshot, "ctaText")
    cta_url = _first(raw, "linkUrl", "link_url", "url") or _first(snapshot, "linkUrl")
    landing = _first(raw, "finalUrl", "final_url") or cta_url

    variant_count = int(
        _first(raw, "variantCount", "ad_variations_count", "totalAdVariations") or 1
    )

    reach = _first(raw, "reachBand", "eu_total_reach", "total_reach")
    impressions = _first(raw, "impressionsBand", "impressions")
    spend = _first(raw, "spendBand", "spend")

    return {
        "platform": "meta",
        "ad_id": str(ad_id),
        "advertiser_name": page_name,
        "advertiser_page_id": str(page_id) if page_id else None,
        "advertiser_url": (
            f"https://www.facebook.com/{page_id}" if page_id else None
        ),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "days_active": days_active,
        "countries": countries or None,
        "languages": languages or None,
        "placements": placements or None,
        "creative_type": _detect_creative_type(raw),
        "media_urls": _extract_media(raw) or None,
        "local_media_paths": None,
        "headline": headline,
        "primary_text": body,
        "description": description,
        "cta_text": cta_text,
        "cta_url": cta_url,
        "landing_url": landing,
        "variant_count": variant_count,
        "reach_band": str(reach) if reach is not None else None,
        "impressions_band": str(impressions) if impressions is not None else None,
        "spend_band": str(spend) if spend is not None else None,
        "raw_json": raw,
    }
