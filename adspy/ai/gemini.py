"""Gemini AI Studio provider — free tier, multimodal, ingests video URLs natively.

Quota (as of 2026-05): 1,500 req/day on Gemini 2.5 Pro, more on Flash. No billing.
"""
from __future__ import annotations

import time

from adspy.ai.base import AnalyzeRequest, AnalyzeResult, Modality
from adspy.config import Settings, get_settings
from adspy.utils.errors import AdspyError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


class GeminiProvider:
    name = "gemini"
    supports: tuple[Modality, ...] = ("text", "image", "video")

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._key = self.settings.gemini_api_key.get_secret_value()

    def healthy(self) -> bool:
        return bool(self._key)

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult:
        if not self._key:
            raise AdspyError("GEMINI_API_KEY not configured")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AdspyError("google-genai package not installed") from exc

        client = genai.Client(api_key=self._key)
        model = "gemini-2.5-pro" if req.modality == "video" else "gemini-2.5-flash"
        parts: list[object] = [req.prompt]
        if req.image_urls:
            for url in req.image_urls:
                parts.append(types.Part.from_uri(file_uri=url, mime_type="image/jpeg"))
        if req.video_url:
            parts.append(types.Part.from_uri(file_uri=req.video_url, mime_type="video/mp4"))

        cfg = types.GenerateContentConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            response_mime_type="application/json" if req.json_mode else None,
        )
        t0 = time.time()
        resp = client.models.generate_content(model=model, contents=parts, config=cfg)
        latency = int((time.time() - t0) * 1000)
        text = getattr(resp, "text", None) or ""
        return AnalyzeResult(
            provider=self.name, model=model, text=text, cost_usd=0.0, latency_ms=latency
        )


__all__ = ["GeminiProvider"]
