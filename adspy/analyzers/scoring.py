from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Reach band -> normalized 0..1 (Meta EU transparency buckets). Conservative midpoints.
REACH_BAND_SCALE: dict[str, float] = {
    "<1000": 0.05,
    "1000-5000": 0.15,
    "5000-10000": 0.25,
    "10000-50000": 0.40,
    "50000-100000": 0.55,
    "100000-500000": 0.70,
    "500000-1000000": 0.85,
    ">1000000": 1.00,
}


@dataclass(frozen=True)
class ScoreInputs:
    days_active: int | None
    variant_count: int | None
    reach_band: str | None
    placements: tuple[str, ...] | None
    first_seen: datetime | None


def _longevity_component(days_active: int | None) -> float:
    if days_active is None or days_active < 0:
        return 0.0
    if days_active >= 90:
        return 1.00
    if days_active >= 60:
        return 0.85
    if days_active >= 30:
        return 0.65
    if days_active >= 14:
        return 0.40
    if days_active >= 7:
        return 0.20
    return 0.05


def _variant_component(variant_count: int | None) -> float:
    if variant_count is None or variant_count <= 0:
        return 0.0
    if variant_count >= 20:
        return 1.00
    if variant_count >= 10:
        return 0.85
    if variant_count >= 5:
        return 0.65
    if variant_count >= 3:
        return 0.40
    if variant_count >= 2:
        return 0.20
    return 0.05


def _reach_component(reach_band: str | None) -> float:
    if not reach_band:
        return 0.0
    return REACH_BAND_SCALE.get(reach_band.strip(), 0.0)


def _placement_component(placements: tuple[str, ...] | None) -> float:
    if not placements:
        return 0.0
    # Meta: 4 placements (facebook, instagram, messenger, audience_network/threads). Cap at 4.
    n = min(len(set(placements)), 4)
    return n / 4.0


def _recency_bonus(
    first_seen: datetime | None, longevity: float, variant: float, reach: float
) -> float:
    """Bonus for very new ads that are *already* showing winner signals."""
    if first_seen is None:
        return 0.0
    age = (datetime.now(UTC) - first_seen).days
    if age > 14:
        return 0.0
    # Only emerging winners — require strength elsewhere before granting the bonus.
    if max(variant, reach) < 0.40 and longevity < 0.20:
        return 0.0
    return 1.0


def winner_score(inputs: ScoreInputs) -> int:
    """Return an integer 0..100 estimating ad-winner likelihood. Pure function."""
    longevity = _longevity_component(inputs.days_active)
    variant = _variant_component(inputs.variant_count)
    reach = _reach_component(inputs.reach_band)
    placement = _placement_component(inputs.placements)
    recency = _recency_bonus(inputs.first_seen, longevity, variant, reach)

    score = (
        0.40 * longevity
        + 0.25 * variant
        + 0.20 * reach
        + 0.10 * placement
        + 0.05 * recency
    )
    return max(0, min(100, round(score * 100)))


def score_ad_row(ad: dict[str, Any]) -> int:
    """Convenience: build ScoreInputs from a normalized-ad dict and score it."""
    placements = ad.get("placements")
    return winner_score(
        ScoreInputs(
            days_active=ad.get("days_active"),
            variant_count=ad.get("variant_count"),
            reach_band=ad.get("reach_band"),
            placements=tuple(placements) if placements else None,
            first_seen=ad.get("first_seen"),
        )
    )
