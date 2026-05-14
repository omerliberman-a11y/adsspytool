"""Offline router tests: verify provider-selection logic without hitting any API."""
import os
from dataclasses import replace

import pytest

from adspy.ai.base import AnalyzeRequest


@pytest.fixture(autouse=True)
def _restore_env() -> None:
    """Saved/restored env around each test so we can poke settings."""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def _fresh_router(**env: str):
    from adspy.config import get_settings

    for k, v in env.items():
        os.environ[k.upper()] = v
    get_settings.cache_clear()
    from adspy.ai.router import AIRouter

    return AIRouter()


def test_text_chain_prefers_configured_primary() -> None:
    router = _fresh_router(ai_text_primary="gemini", gemini_api_key="x", groq_api_key="y")
    chain = router._chain("text")  # type: ignore[attr-defined]
    assert chain[0].name == "gemini"
    assert "groq" in [p.name for p in chain]


def test_vision_chain_excludes_groq() -> None:
    router = _fresh_router(gemini_api_key="x", groq_api_key="y")
    names = [p.name for p in router._chain("image")]  # type: ignore[attr-defined]
    assert "groq" not in names
    assert "gemini" in names


def test_embedding_chain_uses_local_or_cfwai() -> None:
    router = _fresh_router(cf_account_id="a", cf_api_token="t")
    names = [p.name for p in router._chain("embedding")]  # type: ignore[attr-defined]
    assert "cfwai" in names


def test_local_only_forces_ollama() -> None:
    router = _fresh_router(local_only="true", groq_api_key="y", gemini_api_key="x")
    for modality in ("text", "image"):
        names = [p.name for p in router._chain(modality)]  # type: ignore[attr-defined]
        assert names == ["ollama"], f"expected ollama-only for {modality}, got {names}"


def test_analyze_request_dataclass_defaults() -> None:
    req = AnalyzeRequest(modality="text", prompt="hi")
    assert req.json_mode is False
    assert req.temperature == 0.2
    assert replace(req, json_mode=True).json_mode is True
