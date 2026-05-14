"""Last-mile LLM normalizer.

When a classic normalizer raises `NormalizerError` (new field shape, missing
critical fields, partial response), this module asks the AI router to extract
fields from raw_json against the unified-ad schema. The failure + recovered row
are written to `normalization_failures` for offline review and code patching.
"""
from __future__ import annotations

import json
from typing import Any

from adspy.ai.base import AnalyzeRequest
from adspy.ai.router import AIRouter
from adspy.db.session import session_scope
from adspy.models.normalization_failure import NormalizationFailure
from adspy.utils.errors import NormalizerError
from adspy.utils.logging import get_logger

log = get_logger(__name__)

_PROMPT = """You are a strict JSON extractor. Given a raw ad-library record below,
return a single JSON object matching this schema (use null for missing fields,
do not invent values):

{{
  "ad_id": "string",
  "advertiser_name": "string|null",
  "advertiser_page_id": "string|null",
  "first_seen": "ISO 8601 string|null",
  "last_seen": "ISO 8601 string|null",
  "countries": ["ISO country codes"]|null,
  "languages": ["ISO language codes"]|null,
  "placements": ["platform names"]|null,
  "creative_type": "video|image|carousel|text",
  "headline": "string|null",
  "primary_text": "string|null",
  "description": "string|null",
  "cta_text": "string|null",
  "cta_url": "string|null",
  "landing_url": "string|null",
  "variant_count": "integer|null"
}}

RECORD:
{record}

Return ONLY the JSON object, no commentary.
"""


def recover(
    platform: str,
    raw: dict[str, Any],
    *,
    classic_error: NormalizerError,
    router: AIRouter | None = None,
) -> dict[str, Any] | None:
    """Try to LLM-extract a partial unified-ad row. Returns None if recovery fails.

    Always persists the failure (with the recovered row if any) for later code patching.
    """
    router = router or AIRouter()
    prompt = _PROMPT.format(record=json.dumps(raw, default=str)[:8000])
    result_text: str | None = None
    recovered: dict[str, Any] | None = None

    try:
        result = router.analyze(
            AnalyzeRequest(
                modality="text",
                prompt=prompt,
                json_mode=True,
                max_tokens=1024,
                temperature=0.0,
            )
        )
        result_text = result.text
        parsed = json.loads(result_text or "{}")
        if parsed.get("ad_id"):
            parsed["platform"] = platform
            parsed["raw_json"] = raw
            recovered = parsed
    except Exception as exc:  # noqa: BLE001 — any AI/JSON failure is recoverable
        log.warning("llm_fallback_failed", platform=platform, error=str(exc))

    _persist_failure(platform, raw, str(classic_error), result_text, recovered is not None)
    return recovered


def _persist_failure(
    platform: str,
    raw: dict[str, Any],
    classic_error: str,
    llm_output: str | None,
    recovered: bool,
) -> None:
    try:
        with session_scope() as s:
            s.add(
                NormalizationFailure(
                    platform=platform,
                    raw_json=raw,
                    classic_error=classic_error[:2000],
                    llm_output=(llm_output or "")[:8000],
                    recovered=recovered,
                )
            )
    except Exception as exc:  # noqa: BLE001 — never let failure logging break the pipeline
        log.error("normalization_failure_log_failed", error=str(exc))
