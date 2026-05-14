"""Cost-aware AI router. Single entrypoint for the rest of the codebase.

Order of providers per modality is config-driven; on rate-limit / outage the
router falls through to the next provider. Every call records a row in
`ai_calls` for budget observability.
"""
from __future__ import annotations

from adspy.ai.base import AIProvider, AnalyzeRequest, AnalyzeResult, Modality
from adspy.ai.cfwai import CloudflareWorkersAIProvider
from adspy.ai.gemini import GeminiProvider
from adspy.ai.groq import GroqProvider
from adspy.ai.ollama import OllamaProvider
from adspy.config import Settings, get_settings
from adspy.utils.errors import AdspyError
from adspy.utils.logging import get_logger

log = get_logger(__name__)


class AIRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._providers: dict[str, AIProvider] = {
            "gemini": GeminiProvider(self.settings),
            "groq": GroqProvider(self.settings),
            "cfwai": CloudflareWorkersAIProvider(self.settings),
            "ollama": OllamaProvider(self.settings),
        }

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult:
        for provider in self._chain(req.modality):
            if not provider.healthy():
                continue
            try:
                return provider.analyze(req)
            except Exception as exc:
                log.warning(
                    "ai_provider_failed",
                    provider=provider.name,
                    modality=req.modality,
                    error=str(exc),
                )
                continue
        raise AdspyError(f"no healthy AI provider for modality={req.modality}")

    def _chain(self, modality: Modality) -> list[AIProvider]:
        if self.settings.local_only:
            return [self._providers["ollama"]]

        # Pick the configured primary first, then a sensible fallback chain.
        order: list[str]
        if modality == "text":
            order = [self.settings.ai_text_primary, "groq", "gemini", "cfwai", "ollama"]
        elif modality in ("image", "video"):
            order = [self.settings.ai_vision_primary, "gemini", "ollama"]
        elif modality == "embedding":
            order = [self.settings.ai_embedding_primary, "cfwai"]
        else:
            order = []

        seen: set[str] = set()
        out: list[AIProvider] = []
        for name in order:
            if name in seen or name not in self._providers:
                continue
            seen.add(name)
            provider = self._providers[name]
            if modality in provider.supports:
                out.append(provider)
        return out
