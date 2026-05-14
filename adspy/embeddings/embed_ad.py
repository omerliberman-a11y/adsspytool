"""Embed one ad — both copy and (if available) image. Persists to Ad row."""
from __future__ import annotations

import httpx

from adspy.db.session import session_scope
from adspy.embeddings.copy import embed_copy
from adspy.embeddings.image import embed_image_bytes
from adspy.models.ad import Ad
from adspy.utils.logging import get_logger

log = get_logger(__name__)


def embed_one(*, platform: str, ad_id: str) -> None:
    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            return
        if ad.copy_embedding is not None and ad.image_embedding is not None:
            return
        copy_text = " | ".join(
            x for x in (ad.headline, ad.primary_text, ad.description, ad.ai_hook) if x
        )
        media_urls = list(ad.media_urls or [])

    copy_vec = embed_copy(copy_text) if copy_text else None

    image_vec: list[float] | None = None
    if media_urls:
        image_vec = _fetch_and_embed_first_image(media_urls)

    if copy_vec is None and image_vec is None:
        return

    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            return
        if copy_vec is not None:
            ad.copy_embedding = copy_vec
        if image_vec is not None:
            ad.image_embedding = image_vec

    log.info(
        "embed_done",
        platform=platform,
        ad_id=ad_id,
        copy=copy_vec is not None,
        image=image_vec is not None,
    )


def _fetch_and_embed_first_image(urls: list[str]) -> list[float] | None:
    for url in urls:
        low = url.lower()
        if not any(low.endswith(p) for p in (".jpg", ".jpeg", ".png", ".webp")):
            continue
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                return embed_image_bytes(r.content)
        except Exception as exc:  # noqa: BLE001
            log.warning("embed_image_fetch_failed", url=url, error=str(exc))
            continue
    return None
