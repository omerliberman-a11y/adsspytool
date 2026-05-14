"""Snapshot replay worker — extracts media URLs the Graph API doesn't return.

For each ad, we open `ad_snapshot_url` in a headless Playwright browser, intercept
network XHRs + DOM, harvest media URLs, download the assets, compute SHA-256 and
pHash, persist to R2 (or local fs), update the Ad row.

Idempotent: skips ads that already have media_urls populated unless `force=True`.
"""
from __future__ import annotations

from typing import Any

import httpx

from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.storage import get_media_store
from adspy.utils.errors import ScrapeError
from adspy.utils.hashing import phash_bytes, sha256_bytes
from adspy.utils.logging import get_logger

log = get_logger(__name__)

VIDEO_PATTERNS = (".mp4", "video_dashinit", "videoplayback")
IMAGE_PATTERNS = (".jpg", ".jpeg", ".png", ".webp")


def replay_one(*, ad_id: str, snapshot_url: str, force: bool = False) -> None:
    """Resolve media for a single Meta ad. Persists to DB. No-op if already resolved."""
    with session_scope() as s:
        ad = s.get(Ad, ("meta", ad_id))
        if ad is None:
            raise ScrapeError(f"ad meta/{ad_id} not found")
        if ad.media_urls and not force:
            log.info("snapshot_replay_skip", ad_id=ad_id, reason="already_resolved")
            return

    media_urls = _harvest_media(snapshot_url)
    if not media_urls:
        log.warning("snapshot_replay_no_media", ad_id=ad_id)
        return

    store = get_media_store()
    local_paths: list[str] = []
    phashes: list[str] = []
    creative_type = "image"

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for url in media_urls[:8]:  # cap downloads per ad
            try:
                r = client.get(url)
                r.raise_for_status()
                data = r.content
            except httpx.HTTPError as exc:
                log.warning("media_download_failed", url=url, error=str(exc))
                continue
            sha = sha256_bytes(data)
            ext = _ext_for(url)
            key = f"meta/{ad_id}/{sha[:16]}.{ext}"
            store.put(key, data, content_type=_mime_for(ext))
            local_paths.append(key)
            ph = phash_bytes(data)
            if ph:
                phashes.append(ph)
            if ext == "mp4":
                creative_type = "video"
            elif creative_type != "video" and ext in ("jpg", "jpeg", "png", "webp"):
                creative_type = "image"

    if not local_paths:
        log.warning("snapshot_replay_all_downloads_failed", ad_id=ad_id)
        return

    if len(media_urls) > 1 and creative_type == "image":
        creative_type = "carousel"

    with session_scope() as s:
        ad = s.get(Ad, ("meta", ad_id))
        if ad is None:
            return
        ad.media_urls = media_urls
        ad.local_media_paths = local_paths
        ad.media_phash = phashes or None
        ad.creative_type = creative_type

    log.info(
        "snapshot_replay_done",
        ad_id=ad_id,
        media=len(media_urls),
        downloaded=len(local_paths),
        creative_type=creative_type,
    )


def _harvest_media(snapshot_url: str) -> list[str]:
    """Open the snapshot page, capture network + DOM media URLs."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScrapeError("playwright not installed (poetry install)") from exc

    found: list[str] = []
    seen: set[str] = set()

    def _on_request(req: Any) -> None:
        url = req.url
        if not isinstance(url, str):
            return
        low = url.lower()
        if any(p in low for p in VIDEO_PATTERNS) or any(low.endswith(p) for p in IMAGE_PATTERNS):
            if url not in seen:
                seen.add(url)
                found.append(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 1600},
            )
            page = ctx.new_page()
            page.on("request", _on_request)
            page.goto(snapshot_url, wait_until="networkidle", timeout=30000)
            # Scrape DOM-rendered images too — sometimes images are <img src> not XHRs.
            dom_imgs = page.evaluate(
                """() => Array.from(document.images).map(i => i.src).filter(Boolean)"""
            )
            for url in dom_imgs or []:
                if isinstance(url, str) and url not in seen:
                    low = url.lower()
                    if any(low.endswith(p) for p in IMAGE_PATTERNS):
                        seen.add(url)
                        found.append(url)
        finally:
            browser.close()
    return found


def _ext_for(url: str) -> str:
    low = url.lower().split("?")[0]
    for ext in ("mp4", "jpg", "jpeg", "png", "webp"):
        if low.endswith(f".{ext}"):
            return ext
    if "video_dashinit" in low or "videoplayback" in low:
        return "mp4"
    return "bin"


def _mime_for(ext: str) -> str:
    return {
        "mp4": "video/mp4",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
