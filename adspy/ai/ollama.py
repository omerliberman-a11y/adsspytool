"""Ollama provider — local fallback. Zero network cost, zero external dependency.

Use when upstream providers are rate-limited or `LOCAL_ONLY=true`. Vision works
with `llama3.2-vision`, text with `qwen2.5:14b-instruct` (default — both fit on
24GB GPU; smaller variants exist for 8GB cards).
"""
from __future__ import annotations

import time

from adspy.ai.base import AnalyzeRequest, AnalyzeResult, Modality
from adspy.config import Settings, get_settings
from adspy.utils.errors import AdspyError


class OllamaProvider:
    name = "ollama"
    supports: tuple[Modality, ...] = ("text", "image")

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def healthy(self) -> bool:
        try:
            from ollama import Client
        except ImportError:
            return False
        try:
            Client(host=self.settings.ollama_base_url).list()
        except Exception:
            return False
        return True

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult:
        try:
            from ollama import Client
        except ImportError as exc:
            raise AdspyError("ollama package not installed") from exc

        client = Client(host=self.settings.ollama_base_url)
        model = (
            self.settings.ollama_vision_model
            if req.modality == "image"
            else self.settings.ollama_text_model
        )
        messages: list[dict[str, object]] = [{"role": "user", "content": req.prompt}]
        if req.image_urls:
            messages[0]["images"] = req.image_urls  # ollama accepts URLs or base64

        t0 = time.time()
        resp = client.chat(
            model=model,
            messages=messages,
            options={"temperature": req.temperature, "num_predict": req.max_tokens},
            format="json" if req.json_mode else "",
        )
        latency = int((time.time() - t0) * 1000)
        text = resp["message"]["content"] or ""
        return AnalyzeResult(
            provider=self.name, model=model, text=text, cost_usd=0.0, latency_ms=latency
        )
