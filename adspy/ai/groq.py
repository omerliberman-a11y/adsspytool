"""Groq provider — free, fastest text inference. Llama 3.3 70B / Qwen 2.5 72B.

Quota (as of 2026-05): ~30 req/min, 14.4K req/day on free tier. Excellent for
structured extraction and copy rewriting.
"""
from __future__ import annotations

import time

from adspy.ai.base import AnalyzeRequest, AnalyzeResult, Modality
from adspy.config import Settings, get_settings
from adspy.utils.errors import AdspyError


class GroqProvider:
    name = "groq"
    supports: tuple[Modality, ...] = ("text",)

    def __init__(self, settings: Settings | None = None, model: str = "llama-3.3-70b-versatile"):
        self.settings = settings or get_settings()
        self.model = model
        self._key = self.settings.groq_api_key.get_secret_value()

    def healthy(self) -> bool:
        return bool(self._key)

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult:
        if not self._key:
            raise AdspyError("GROQ_API_KEY not configured")
        try:
            from groq import Groq
        except ImportError as exc:
            raise AdspyError("groq package not installed") from exc

        client = Groq(api_key=self._key)
        t0 = time.time()
        kwargs: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": req.prompt}],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        latency = int((time.time() - t0) * 1000)
        text = resp.choices[0].message.content or ""
        return AnalyzeResult(
            provider=self.name, model=self.model, text=text, cost_usd=0.0, latency_ms=latency
        )
