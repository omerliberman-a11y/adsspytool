from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

Modality = Literal["text", "image", "video", "embedding"]


@dataclass
class AnalyzeRequest:
    modality: Modality
    prompt: str
    image_urls: list[str] | None = None
    video_url: str | None = None
    text_to_embed: str | None = None
    # Hints for the router. JSON-mode = ask for structured JSON output.
    json_mode: bool = False
    max_tokens: int = 1024
    temperature: float = 0.2


@dataclass
class AnalyzeResult:
    provider: str
    model: str
    text: str | None = None
    embedding: list[float] | None = None
    cost_usd: float = 0.0
    latency_ms: int = 0


class AIProvider(Protocol):
    name: str
    supports: tuple[Modality, ...]

    def analyze(self, req: AnalyzeRequest) -> AnalyzeResult: ...

    def healthy(self) -> bool: ...
