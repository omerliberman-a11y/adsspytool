from datetime import UTC, datetime, timedelta

import pytest

from adspy.scrapers.meta.normalizer import normalize_meta_ad
from adspy.utils.errors import NormalizerError


def _now() -> datetime:
    return datetime.now(UTC)


def test_missing_id_raises() -> None:
    with pytest.raises(NormalizerError):
        normalize_meta_ad({"pageName": "Acme"})


def test_minimal_record() -> None:
    raw = {
        "adArchiveID": "12345",
        "pageName": "Acme",
        "pageID": "999",
        "body": "Stop wasting money on cold plunges. Try ours.",
    }
    ad = normalize_meta_ad(raw)
    assert ad["platform"] == "meta"
    assert ad["ad_id"] == "12345"
    assert ad["advertiser_name"] == "Acme"
    assert ad["advertiser_page_id"] == "999"
    assert ad["primary_text"].startswith("Stop wasting")
    assert ad["creative_type"] == "text"


def test_video_creative_detection() -> None:
    raw = {"adArchiveID": "1", "videoHdUrl": "https://example.com/v.mp4"}
    ad = normalize_meta_ad(raw)
    assert ad["creative_type"] == "video"
    assert "https://example.com/v.mp4" in (ad["media_urls"] or [])


def test_image_creative_detection() -> None:
    raw = {"adArchiveID": "2", "originalImageUrl": "https://example.com/i.jpg"}
    ad = normalize_meta_ad(raw)
    assert ad["creative_type"] == "image"


def test_carousel_detection() -> None:
    raw = {
        "adArchiveID": "3",
        "cards": [
            {"originalImageUrl": "https://example.com/a.jpg"},
            {"originalImageUrl": "https://example.com/b.jpg"},
        ],
    }
    ad = normalize_meta_ad(raw)
    assert ad["creative_type"] == "carousel"
    assert len(ad["media_urls"] or []) >= 2


def test_days_active_computed() -> None:
    start = _now() - timedelta(days=42)
    end = _now()
    raw = {
        "adArchiveID": "4",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
    }
    ad = normalize_meta_ad(raw)
    assert ad["days_active"] is not None
    assert 40 <= ad["days_active"] <= 44


def test_unix_timestamps_supported() -> None:
    start = int((_now() - timedelta(days=10)).timestamp())
    raw = {"adArchiveID": "5", "startDate": start}
    ad = normalize_meta_ad(raw)
    assert ad["first_seen"] is not None
    assert ad["days_active"] is not None and ad["days_active"] >= 9


def test_raw_json_preserved() -> None:
    raw = {"adArchiveID": "6", "extra": {"thing": 1}}
    ad = normalize_meta_ad(raw)
    assert ad["raw_json"] is raw


def test_snake_case_keys_accepted() -> None:
    raw = {
        "ad_archive_id": "7",
        "page_name": "Acme",
        "page_id": "111",
        "body": "Hello",
    }
    ad = normalize_meta_ad(raw)
    assert ad["ad_id"] == "7"
    assert ad["advertiser_name"] == "Acme"
