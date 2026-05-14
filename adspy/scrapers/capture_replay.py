"""Capture-replay base. Two-step pattern used by every non-Graph-API source:

  1. CAPTURE: open a real browser (Playwright), let operator log in once if needed,
     store cookies + headers + a representative GraphQL/RPC request as a session blob.
  2. REPLAY: use those cookies + headers to fire the same request via httpx in a
     loop, with no browser. Orders of magnitude cheaper than running Playwright
     against every ad.

Sessions live in `Settings.session_store_dir/<platform>.json`. The runner checks
for staleness (rolling 7d default); on 401/403 the worker logs `session_stale`
and the operator re-captures.

Concrete scrapers (`x/`, `tiktok/`, `google_ads/`, `linkedin/`) subclass `Replayer`
and supply (a) the URL template, (b) the request body builder, (c) the response
parser. Capture flows are interactive and live in `scripts/capture_*.py` (added
per-platform).
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from adspy.config import get_settings
from adspy.utils.errors import ScrapeError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class Session:
    platform: str
    cookies: dict[str, str]
    headers: dict[str, str]
    captured_at: datetime

    def is_stale(self, max_age_days: int = 7) -> bool:
        return datetime.now(UTC) - self.captured_at > timedelta(days=max_age_days)

    @classmethod
    def load(cls, platform: str) -> Session:
        path = _session_path(platform)
        if not path.exists():
            raise ScrapeError(
                f"No captured session for '{platform}'. "
                f"Run: python -m adspy.scrapers.capture_replay capture --platform {platform}"
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            platform=data["platform"],
            cookies=data["cookies"],
            headers=data["headers"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
        )

    def save(self) -> None:
        path = _session_path(self.platform)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "platform": self.platform,
                    "cookies": self.cookies,
                    "headers": self.headers,
                    "captured_at": self.captured_at.isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _session_path(platform: str) -> Path:
    return Path(get_settings().session_store_dir) / f"{platform}.json"


class Replayer:
    """Subclass and override `request_for_page` + `parse_response`."""

    platform: str  # set in subclass

    def __init__(self, session: Session | None = None) -> None:
        if not hasattr(self, "platform"):
            raise TypeError(f"{type(self).__name__} must set class attr 'platform'")
        self.session = session or Session.load(self.platform)
        if self.session.is_stale():
            log.warning("session_stale", platform=self.platform, captured=self.session.captured_at)
        self._client = httpx.Client(
            cookies=self.session.cookies,
            headers=self.session.headers,
            timeout=get_settings().scrape_timeout_secs,
            follow_redirects=True,
        )

    def __enter__(self) -> Replayer:
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    def request_for_page(self, cursor: str | None) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Return (url, params, json_body). Override per platform."""
        raise NotImplementedError

    def parse_response(self, payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
        """Return (items, next_cursor). Override per platform."""
        raise NotImplementedError

    def iter_pages(self) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        cap = get_settings().scrape_max_items_per_run
        emitted = 0
        while True:
            url, params, body = self.request_for_page(cursor)
            r = self._client.post(url, params=params, json=body) if body else self._client.get(
                url, params=params
            )
            if r.status_code in (401, 403):
                raise ScrapeError(
                    f"{self.platform} session rejected ({r.status_code}). Re-capture required."
                )
            r.raise_for_status()
            items, cursor = self.parse_response(r.json())
            for item in items:
                yield item
                emitted += 1
                if emitted >= cap:
                    return
            if not cursor:
                return
