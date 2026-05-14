"""Tests for the Meta Ad Library Graph API normalizer.

Field shape comes from facebook.com/ads/library/api docs:
https://developers.facebook.com/docs/marketing-api/reference/archived-ad/
"""
from datetime import UTC, datetime, timedelta

import pytest

from adspy.normalize.meta import normalize_meta_ad
from adspy.utils.errors import NormalizerError


def _record(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "100000000000001",
        "page_id": "999",
        "page_name": "Acme Co",
        "ad_creative_bodies": ["Stop wasting money on cold plunges. Try ours."],
        "ad_creative_link_titles": ["Cold Plunge for $499"],
        "ad_creative_link_descriptions": ["Free shipping, 30-day guarantee."],
        "ad_creative_link_captions": ["Shop Now"],
        "ad_snapshot_url": "https://www.facebook.com/ads/library/?id=100000000000001",
        "ad_delivery_start_time": (datetime.now(UTC) - timedelta(days=42)).isoformat(),
        "ad_delivery_stop_time": datetime.now(UTC).isoformat(),
        "publisher_platforms": ["facebook", "instagram"],
        "languages": ["en"],
    }
    base.update(overrides)
    return base


def test_missing_id_raises() -> None:
    with pytest.raises(NormalizerError):
        normalize_meta_ad({"page_name": "Acme"})


def test_minimal_record() -> None:
    ad = normalize_meta_ad(_record())
    assert ad["platform"] == "meta"
    assert ad["ad_id"] == "100000000000001"
    assert ad["advertiser_name"] == "Acme Co"
    assert ad["advertiser_page_id"] == "999"
    assert ad["headline"] == "Cold Plunge for $499"
    assert ad["primary_text"].startswith("Stop wasting")
    assert ad["cta_text"] == "Shop Now"
    assert "facebook" in ad["placements"]
    assert ad["landing_url"].startswith("https://www.facebook.com/ads/library")


def test_days_active_computed() -> None:
    ad = normalize_meta_ad(_record())
    assert ad["days_active"] is not None
    assert 40 <= ad["days_active"] <= 44


def test_carousel_via_multiple_bodies() -> None:
    ad = normalize_meta_ad(
        _record(ad_creative_bodies=["Body 1", "Body 2", "Body 3"])
    )
    assert ad["creative_type"] == "carousel"
    assert ad["variant_count"] == 3


def test_carousel_via_multiple_titles() -> None:
    ad = normalize_meta_ad(
        _record(ad_creative_link_titles=["Title 1", "Title 2"])
    )
    assert ad["creative_type"] == "carousel"


def test_text_only_creative() -> None:
    ad = normalize_meta_ad(_record(ad_creative_link_titles=["one title"]))
    assert ad["creative_type"] == "text"


def test_reach_band_parsed_from_dict() -> None:
    ad = normalize_meta_ad(_record(eu_total_reach={"lower_bound": "10000", "upper_bound": "50000"}))
    assert ad["reach_band"] == "10000-50000"


def test_spend_band_parsed_from_dict() -> None:
    ad = normalize_meta_ad(_record(spend={"lower_bound": "1000", "upper_bound": "5000"}))
    assert ad["spend_band"] == "1000-5000"


def test_open_ended_reach_band() -> None:
    ad = normalize_meta_ad(_record(eu_total_reach={"lower_bound": "1000000"}))
    assert ad["reach_band"] == ">1000000"


def test_raw_json_preserved() -> None:
    raw = _record()
    ad = normalize_meta_ad(raw)
    assert ad["raw_json"] is raw


def test_advertiser_url_built_from_page_id() -> None:
    ad = normalize_meta_ad(_record())
    assert ad["advertiser_url"] == "https://www.facebook.com/999"


def test_media_urls_pending() -> None:
    """media_urls are populated by the snapshot-replay worker, not the Graph normalizer."""
    ad = normalize_meta_ad(_record())
    assert ad["media_urls"] is None


def test_countries_from_delivery_by_region() -> None:
    ad = normalize_meta_ad(
        _record(
            delivery_by_region=[
                {"region": "California", "percentage": "0.3"},
                {"region": "Texas", "percentage": "0.2"},
            ]
        )
    )
    assert ad["countries"] == ["California", "Texas"]
