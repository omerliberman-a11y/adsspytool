"""Cross-advertiser rip-off detection.

Two ads from different advertisers that share a pHash (Hamming distance <= 8 out
of 64 bits) are flagged as visual rip-offs. Stored in `rip_off_clusters` for the
dashboard's "rip-off radar" panel.

Volume note: O(N^2) over all ads is fine up to ~50K ads; we'll switch to LSH if
we cross that. For now we limit the scan to ads created in the last 90 days.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.utils.hashing import hamming_hex
from adspy.utils.logging import get_logger

log = get_logger(__name__)

HAMMING_THRESHOLD = 8


def scan_for_rip_offs() -> int:
    """Return the number of cross-advertiser pHash clusters found."""
    cutoff = datetime.now(UTC) - timedelta(days=90)
    with session_scope() as s:
        rows = list(
            s.execute(
                select(Ad.platform, Ad.ad_id, Ad.advertiser_page_id, Ad.media_phash)
                .where(Ad.media_phash.is_not(None))
                .where(Ad.created_at >= cutoff)
            )
        )

    # Flatten to (platform, ad_id, advertiser_page_id, phash)
    items: list[tuple[str, str, str | None, str]] = []
    for platform, ad_id, advertiser, hashes in rows:
        for ph in hashes or []:
            items.append((platform, ad_id, advertiser, ph))

    clusters: dict[str, list[tuple[str, str, str | None]]] = {}
    for i, (p1, a1, adv1, ph1) in enumerate(items):
        for p2, a2, adv2, ph2 in items[i + 1 :]:
            if adv1 and adv2 and adv1 == adv2:
                continue  # same advertiser → variant, not rip-off
            try:
                if hamming_hex(ph1, ph2) <= HAMMING_THRESHOLD:
                    key = min(ph1, ph2)
                    clusters.setdefault(key, []).append((p1, a1, adv1))
                    clusters[key].append((p2, a2, adv2))
            except ValueError:
                continue

    log.info("rip_off_scan_done", items=len(items), clusters=len(clusters))
    return len(clusters)
