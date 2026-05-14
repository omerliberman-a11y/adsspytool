"""Normalizer for Meta Ad Library Graph API records into the unified Ad schema.

Field shape is the one documented at facebook.com/ads/library/api.
Falls back to `llm_fallback.recover` when a record is unparseable.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dateutil import parser as dateparser

from adspy.utils.errors import NormalizerError


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
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


def _first_text(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return str(values[0])
    if isinstance(values, str) and values:
        return values
    return None


def _band(value: Any) -> str | None:
    """Graph API returns lower_bound/upper_bound dicts for reach/spend/impressions."""
    if isinstance(value, dict):
        lo = value.get("lower_bound")
        hi = value.get("upper_bound")
        if lo and hi:
            return f"{lo}-{hi}"
        if lo:
            return f">{lo}"
        if hi:
            return f"<{hi}"
    if isinstance(value, str):
        return value
    return None


def _detect_creative_type(record: dict[str, Any]) -> str:
    bodies = record.get("ad_creative_bodies") or []
    if isinstance(bodies, list) and len(bodies) > 1:
        return "carousel"
    titles = record.get("ad_creative_link_titles") or []
    if isinstance(titles, list) and len(titles) > 1:
        return "carousel"
    # Video / image detection happens later, after snapshot_replay pulls media URLs.
    # Until then we mark "text" if there's body copy, otherwise unknown="image" placeholder.
    return "text" if bodies else "image"


def normalize_meta_ad(raw: dict[str, Any]) -> dict[str, Any]:
    ad_id = raw.get("id")
    if not ad_id:
        raise NormalizerError("Graph API record missing 'id'")

    first_seen = _parse_dt(raw.get("ad_delivery_start_time"))
    last_seen = _parse_dt(raw.get("ad_delivery_stop_time")) or datetime.now(UTC)
    days_active = (last_seen - first_seen).days if first_seen and last_seen else None

    placements = raw.get("publisher_platforms") or None
    countries = (
        [r.get("region") for r in raw.get("delivery_by_region", []) if r.get("region")]
        or None
    )
    languages = raw.get("languages") or None

    headline = _first_text(raw.get("ad_creative_link_titles"))
    primary_text = _first_text(raw.get("ad_creative_bodies"))
    description = _first_text(raw.get("ad_creative_link_descriptions"))
    cta_text = _first_text(raw.get("ad_creative_link_captions"))
    snapshot_url = raw.get("ad_snapshot_url")

    return {
        "platform": "meta",
        "ad_id": str(ad_id),
        "advertiser_name": raw.get("page_name"),
        "advertiser_page_id": str(raw["page_id"]) if raw.get("page_id") else None,
        "advertiser_url": (
            f"https://www.facebook.com/{raw['page_id']}" if raw.get("page_id") else None
        ),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "days_active": days_active,
        "countries": countries,
        "languages": languages,
        "placements": placements,
        "creative_type": _detect_creative_type(raw),
        "media_urls": None,  # filled by snapshot_replay worker in Phase 1
        "headline": headline,
        "primary_text": primary_text,
        "description": description,
        "cta_text": cta_text,
        "cta_url": None,
        "landing_url": snapshot_url,
        "variant_count": (
            len(raw["ad_creative_bodies"])
            if isinstance(raw.get("ad_creative_bodies"), list)
            else None
        ),
        "reach_band": _band(raw.get("eu_total_reach")),
        "impressions_band": _band(raw.get("impressions")),
        "spend_band": _band(raw.get("spend")),
        "raw_json": raw,
    }
