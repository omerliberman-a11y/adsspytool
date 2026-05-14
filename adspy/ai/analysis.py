"""Creative analysis workflow.

For each ad:
  1. If video/image, send the first media to Gemini for visual analysis.
  2. Send copy + visual notes to a text model (Groq) for structured extraction:
     hook_type, awareness_stage, copy_framework, ai_hook, ai_angle, ai_offer,
     ai_summary, and 3 rewritten copy variants in our brand voice.
  3. Persist to the Ad row + log an `ai_calls` entry per provider call.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from adspy.ai.base import AnalyzeRequest, AnalyzeResult
from adspy.ai.router import AIRouter
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.ai_call import AICall
from adspy.utils.logging import get_logger

log = get_logger(__name__)

HOOK_TYPES = (
    "curiosity",
    "authority",
    "fear",
    "problem_agitation",
    "transformation",
    "before_after",
    "social_proof",
    "contrarian",
    "pattern_interrupt",
    "listicle",
    "qa",
)
FRAMEWORKS = ("PAS", "AIDA", "FAB", "4U", "BAB", "RMBC", "AIDCA", "story")

_VISION_PROMPT = (
    "You are an expert direct-response ad analyst. Examine the ad creative and "
    "describe in 2-4 sentences: the visual hook (first 1-3 seconds for video, "
    "or the dominant element for images), the proof element if any (testimonial, "
    "before/after, demo), and any urgency or scarcity cues visible. Return ONLY "
    "the description, no preamble."
)


def _structured_prompt(copy_text: str, visual_notes: str | None, brand_voice: str = "") -> str:
    return (
        "You are an expert direct-response copywriter and ad strategist. Analyze "
        "this ad and return a SINGLE valid JSON object with EXACTLY these keys "
        "and no others:\n"
        "{\n"
        '  "hook_type": one of '
        + json.dumps(list(HOOK_TYPES))
        + ",\n"
        '  "awareness_stage": integer 1-5 (Schwartz: 1=unaware, 5=most-aware),\n'
        '  "copy_framework": one of '
        + json.dumps(list(FRAMEWORKS))
        + ",\n"
        '  "ai_hook": "the actual hook line, as it appears or paraphrased in <=12 words",\n'
        '  "ai_angle": "the angle/promise the ad is making (one sentence)",\n'
        '  "ai_offer": "what is being offered (price, guarantee, bonuses) — null if unclear",\n'
        '  "ai_summary": "two-sentence summary of why this ad works",\n'
        '  "ai_rewritten_copy": ["three", "alternate", "copies in same structure, '
        + ("our brand voice: " + brand_voice if brand_voice else "neutral persuasive voice")
        + '"]\n'
        "}\n\n"
        "CREATIVE COPY:\n"
        + (copy_text or "(no copy)")
        + "\n\n"
        + ("VISUAL NOTES:\n" + visual_notes + "\n" if visual_notes else "")
        + "Return ONLY the JSON object."
    )


def analyze_one(*, platform: str, ad_id: str, brand_voice: str = "") -> None:
    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            log.warning("analyze_skip_missing", platform=platform, ad_id=ad_id)
            return
        copy_text = " | ".join(
            x for x in (ad.headline, ad.primary_text, ad.description) if x
        ) or "(no copy)"
        creative_type = ad.creative_type or "text"
        media_urls = list(ad.media_urls or [])
        already_analyzed = bool(ad.ai_summary)

    if already_analyzed:
        log.info("analyze_skip_already_done", platform=platform, ad_id=ad_id)
        return

    router = AIRouter()
    visual_notes = None

    if creative_type in ("image", "video", "carousel") and media_urls:
        try:
            res = router.analyze(
                AnalyzeRequest(
                    modality="video" if creative_type == "video" else "image",
                    prompt=_VISION_PROMPT,
                    image_urls=media_urls[:1] if creative_type != "video" else None,
                    video_url=media_urls[0] if creative_type == "video" else None,
                    max_tokens=512,
                )
            )
            visual_notes = res.text or None
            _log_ai_call(res, purpose="vision_analysis", prompt_len=len(_VISION_PROMPT))
        except Exception as exc:  # noqa: BLE001
            log.warning("vision_analysis_failed", platform=platform, ad_id=ad_id, error=str(exc))

    structured_prompt = _structured_prompt(copy_text, visual_notes, brand_voice=brand_voice)
    try:
        res = router.analyze(
            AnalyzeRequest(
                modality="text",
                prompt=structured_prompt,
                json_mode=True,
                max_tokens=2048,
                temperature=0.3,
            )
        )
        _log_ai_call(res, purpose="structured_extraction", prompt_len=len(structured_prompt))
    except Exception as exc:  # noqa: BLE001
        log.error("structured_extraction_failed", platform=platform, ad_id=ad_id, error=str(exc))
        return

    parsed = _safe_parse(res.text or "")
    if not parsed:
        log.warning("structured_parse_failed", platform=platform, ad_id=ad_id)
        return

    with session_scope() as s:
        ad = s.get(Ad, (platform, ad_id))
        if ad is None:
            return
        ad.hook_type = _clean_enum(parsed.get("hook_type"), HOOK_TYPES)
        ad.awareness_stage = _clean_int(parsed.get("awareness_stage"), low=1, high=5)
        ad.copy_framework = _clean_enum(parsed.get("copy_framework"), FRAMEWORKS)
        ad.ai_hook = _clean_str(parsed.get("ai_hook"), max_len=200)
        ad.ai_angle = _clean_str(parsed.get("ai_angle"), max_len=400)
        ad.ai_offer = _clean_str(parsed.get("ai_offer"), max_len=400)
        ad.ai_summary = _clean_str(parsed.get("ai_summary"), max_len=800)
        ad.ai_rewritten_copy = _clean_list(parsed.get("ai_rewritten_copy"))

    log.info(
        "analyze_done",
        platform=platform,
        ad_id=ad_id,
        hook=ad.hook_type if isinstance(ad, Ad) else None,
    )


def _safe_parse(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[-1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except (ValueError, json.JSONDecodeError):
        return None


def _clean_enum(value: Any, allowed: tuple[str, ...]) -> str | None:
    if isinstance(value, str) and value in allowed:
        return value
    return None


def _clean_int(value: Any, *, low: int, high: int) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if low <= n <= high else None


def _clean_str(value: Any, *, max_len: int) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()[:max_len]
    return None


def _clean_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        out = [str(x).strip() for x in value if isinstance(x, str) and x.strip()]
        return out[:5] if out else None
    return None


def _log_ai_call(result: AnalyzeResult, *, purpose: str, prompt_len: int) -> None:
    try:
        with session_scope() as s:
            s.add(
                AICall(
                    provider=result.provider,
                    model=result.model,
                    modality="text" if result.text else "embedding",
                    purpose=purpose,
                    prompt_chars=prompt_len,
                    output_chars=len(result.text or ""),
                    latency_ms=result.latency_ms,
                    cost_usd=result.cost_usd,
                )
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("ai_call_log_failed", error=str(exc))


def analyze_batch(limit: int = 50) -> int:
    """Analyze all ads that don't yet have ai_summary populated. Returns count processed."""
    from sqlalchemy import select

    with session_scope() as s:
        stmt = (
            select(Ad.platform, Ad.ad_id)
            .where(Ad.ai_summary.is_(None))
            .limit(limit)
        )
        rows = list(s.execute(stmt))

    n = 0
    for platform, ad_id in rows:
        try:
            analyze_one(platform=platform, ad_id=ad_id)
            n += 1
        except Exception as exc:  # noqa: BLE001
            log.error("analyze_batch_item_failed", ad_id=ad_id, error=str(exc))
    return n


_ = datetime.now  # keep import alive for future use
_ = UTC
