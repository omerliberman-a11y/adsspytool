"""Cloudflare Workers AI — free tier, generous (10K neurons/day).

Used primarily for embeddings (BGE / m2-bert / others available natively on CF).
"""
from __future__ import annotations

import time

import httpx

from adspy.ai.base import AnalyzeRequest, AnalyzeResult, Modality
from adspy.config import Settings, get_settings
from adspy.utils.errors import AdspyError


class CloudflareWorkersAIProvider:
    name = "cfwai"
    supports: tuple[Modality, ...] = ("text", "embedding")

    EMBED_MODEL = "@cf/baai/bge-large-en-v1.5"
    TEXT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._account = self.settings.cf_account_id
        self._token = self.settings.cf_api_token.get_secret_value()

    def healthy(self) -> bool:
        return bool(self._account and self._token)

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult:
        if not (self._account and self._token):
            raise AdspyError("CF_ACCOUNT_ID / CF_API_TOKEN not configured")

        if req.modality == "embedding":
            return self._embed(req.text_to_embed or req.prompt)
        if req.modality == "text":
            return self._chat(req)
        raise AdspyError(f"cfwai does not support modality={req.modality}")

    def _embed(self, text: str) -> AnalyzeResult:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self._account}"
            f"/ai/run/{self.EMBED_MODEL}"
        )
        t0 = time.time()
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            json={"text": [text]},
            timeout=60,
        )
        r.raise_for_status()
        latency = int((time.time() - t0) * 1000)
        data = r.json()["result"]["data"][0]
        return AnalyzeResult(
            provider=self.name,
            model=self.EMBED_MODEL,
            embedding=data,
            cost_usd=0.0,
            latency_ms=latency,
        )

    def _chat(self, req: AnalyzeRequest) -> AnalyzeResult:
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self._account}"
            f"/ai/run/{self.TEXT_MODEL}"
        )
        t0 = time.time()
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            json={
                "messages": [{"role": "user", "content": req.prompt}],
                "temperature": req.temperature,
                "max_tokens": req.max_tokens,
            },
            timeout=120,
        )
        r.raise_for_status()
        latency = int((time.time() - t0) * 1000)
        return AnalyzeResult(
            provider=self.name,
            model=self.TEXT_MODEL,
            text=r.json()["result"]["response"],
            cost_usd=0.0,
            latency_ms=latency,
        )
