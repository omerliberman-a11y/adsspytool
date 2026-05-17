"""Conversational agent over the adspy DB — Groq tool-use.

Architecture:
  user message
    ↓
  Groq Llama 3.3 70B with a function-calling spec covering the most useful
  read-only operations against our DB:
    - search_ads(filters)
    - get_ad(platform, ad_id)
    - top_advertisers(platform?, limit?)
    - top_destinations(limit?, affiliate_only?)
    - hook_breakdown(platform?)
    - similar_ads(platform, ad_id, by)
    - list_competitors()
  ↓
  Tool calls execute against Postgres + pgvector, results re-fed into the
  model for the final natural-language answer.

All tools are read-only. The router uses Groq exclusively (fast + free) — no
Gemini, no fallback chain, because we want sub-second response time for chat.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import desc, func, select

from adspy.config import get_settings
from adspy.db.session import session_scope
from adspy.models.ad import Ad
from adspy.models.competitor import Competitor
from adspy.utils.errors import AdspyError
from adspy.utils.logging import get_logger

log = get_logger(__name__)

ALLOWED_PLATFORMS = {"meta", "tiktok", "x", "google", "linkedin"}


# --- tool implementations ---------------------------------------------------

def tool_search_ads(
    platform: str | None = None,
    min_score: int | None = None,
    hook_type: str | None = None,
    creative_type: str | None = None,
    days_active_gte: int | None = None,
    country: str | None = None,
    advertiser_contains: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search ads by structured filters."""
    stmt = select(Ad)
    if platform and platform in ALLOWED_PLATFORMS:
        stmt = stmt.where(Ad.platform == platform)
    if min_score is not None:
        stmt = stmt.where(Ad.winner_score >= int(min_score))
    if hook_type:
        stmt = stmt.where(Ad.hook_type == hook_type)
    if creative_type:
        stmt = stmt.where(Ad.creative_type == creative_type)
    if days_active_gte is not None:
        stmt = stmt.where(Ad.days_active >= int(days_active_gte))
    if country:
        stmt = stmt.where(Ad.countries.any(country.upper()))
    if advertiser_contains:
        stmt = stmt.where(Ad.advertiser_name.ilike(f"%{advertiser_contains}%"))
    stmt = stmt.order_by(Ad.winner_score.desc().nullslast()).limit(min(limit, 50))

    with session_scope() as s:
        rows = list(s.scalars(stmt))
        return {
            "count": len(rows),
            "items": [_summarize_ad(a) for a in rows],
        }


def tool_get_ad(platform: str, ad_id: str) -> dict[str, Any]:
    """Get one ad with all details (incl. AI fields)."""
    with session_scope() as s:
        a = s.get(Ad, (platform, ad_id))
        if a is None:
            return {"error": "ad not found"}
        return _full_ad(a)


def tool_top_advertisers(platform: str | None = None, limit: int = 10) -> dict[str, Any]:
    """Top advertisers by ad count, optionally filtered by platform."""
    stmt = (
        select(
            Ad.advertiser_name,
            Ad.platform,
            func.count().label("n"),
            func.avg(Ad.winner_score).label("avg_score"),
        )
        .where(Ad.advertiser_name.is_not(None))
        .group_by(Ad.advertiser_name, Ad.platform)
        .order_by(desc("n"))
        .limit(min(limit, 50))
    )
    if platform and platform in ALLOWED_PLATFORMS:
        stmt = stmt.where(Ad.platform == platform)
    with session_scope() as s:
        rows = list(s.execute(stmt))
        return {
            "items": [
                {
                    "advertiser": r.advertiser_name,
                    "platform": r.platform,
                    "ad_count": int(r.n),
                    "avg_winner_score": round(float(r.avg_score or 0), 1),
                }
                for r in rows
            ]
        }


def tool_top_destinations(limit: int = 10, affiliate_only: bool = False) -> dict[str, Any]:
    """Top destination domains across resolved ads."""
    stmt = (
        select(Ad.final_domain, Ad.affiliate_network, func.count().label("n"))
        .where(Ad.final_domain.is_not(None))
        .group_by(Ad.final_domain, Ad.affiliate_network)
        .order_by(desc("n"))
        .limit(min(limit, 50))
    )
    if affiliate_only:
        stmt = stmt.where(Ad.affiliate_network.is_not(None))
    with session_scope() as s:
        rows = list(s.execute(stmt))
        return {
            "items": [
                {
                    "domain": r.final_domain,
                    "ad_count": int(r.n),
                    "affiliate_network": r.affiliate_network,
                }
                for r in rows
            ]
        }


def tool_hook_breakdown(platform: str | None = None) -> dict[str, Any]:
    """Distribution of hook types across ads."""
    stmt = (
        select(Ad.hook_type, func.count())
        .where(Ad.hook_type.is_not(None))
        .group_by(Ad.hook_type)
        .order_by(desc(func.count()))
    )
    if platform and platform in ALLOWED_PLATFORMS:
        stmt = stmt.where(Ad.platform == platform)
    with session_scope() as s:
        rows = list(s.execute(stmt))
    return {"items": [{"hook": r[0], "count": int(r[1])} for r in rows]}


def tool_similar_ads(platform: str, ad_id: str, by: str = "copy", limit: int = 5) -> dict[str, Any]:
    """Nearest neighbours by copy or image embedding."""
    if by not in ("copy", "image"):
        return {"error": "by must be 'copy' or 'image'"}
    with session_scope() as s:
        anchor = s.get(Ad, (platform, ad_id))
        if anchor is None:
            return {"error": "anchor not found"}
        vec = anchor.copy_embedding if by == "copy" else anchor.image_embedding
        if vec is None:
            return {"error": f"anchor has no {by}_embedding"}
        col = Ad.copy_embedding if by == "copy" else Ad.image_embedding
        dist = col.cosine_distance(vec)
        rows = list(
            s.execute(
                select(Ad, dist.label("d"))
                .where(col.is_not(None))
                .where(~((Ad.platform == platform) & (Ad.ad_id == ad_id)))
                .order_by("d")
                .limit(min(limit, 20))
            )
        )
        return {
            "anchor": _summarize_ad(anchor),
            "items": [{**_summarize_ad(a), "distance": float(d)} for a, d in rows],
        }


def tool_list_competitors(limit: int = 50) -> dict[str, Any]:
    with session_scope() as s:
        rows = list(s.scalars(select(Competitor).order_by(Competitor.created_at.desc()).limit(limit)))
        return {
            "items": [
                {
                    "id": c.id,
                    "domain": c.domain,
                    "name": c.name,
                    "fb_page_id": c.fb_page_id,
                    "tech_stack": c.tech_stack,
                    "tags": c.tags,
                }
                for c in rows
            ]
        }


# --- (de)serialization helpers ----------------------------------------------

def _summarize_ad(a: Ad) -> dict[str, Any]:
    return {
        "platform": a.platform,
        "ad_id": a.ad_id,
        "advertiser": a.advertiser_name,
        "headline": a.headline,
        "ai_hook": a.ai_hook,
        "hook_type": a.hook_type,
        "winner_score": a.winner_score,
        "days_active": a.days_active,
        "creative_type": a.creative_type,
        "final_domain": a.final_domain,
        "affiliate_network": a.affiliate_network,
    }


def _full_ad(a: Ad) -> dict[str, Any]:
    return {
        **_summarize_ad(a),
        "primary_text": a.primary_text,
        "ai_summary": a.ai_summary,
        "ai_angle": a.ai_angle,
        "ai_offer": a.ai_offer,
        "ai_rewritten_copy": a.ai_rewritten_copy,
        "copy_framework": a.copy_framework,
        "awareness_stage": a.awareness_stage,
        "variant_count": a.variant_count,
        "reach_band": a.reach_band,
        "countries": a.countries,
        "placements": a.placements,
        "media_urls": a.media_urls,
        "source_url": a.source_url,
        "final_url": a.final_url,
    }


# --- tool registry + spec ----------------------------------------------------

TOOLS: dict[str, Any] = {
    "search_ads": tool_search_ads,
    "get_ad": tool_get_ad,
    "top_advertisers": tool_top_advertisers,
    "top_destinations": tool_top_destinations,
    "hook_breakdown": tool_hook_breakdown,
    "similar_ads": tool_similar_ads,
    "list_competitors": tool_list_competitors,
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_ads",
            "description": "Search ads with filters. Returns up to 50 ads sorted by winner_score desc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": list(ALLOWED_PLATFORMS)},
                    "min_score": {"type": "integer"},
                    "hook_type": {
                        "type": "string",
                        "description": "e.g. curiosity, authority, problem_agitation, before_after, social_proof, transformation, contrarian, pattern_interrupt, listicle, qa, fear",
                    },
                    "creative_type": {"type": "string", "enum": ["video", "image", "carousel", "text"]},
                    "days_active_gte": {"type": "integer"},
                    "country": {"type": "string", "description": "ISO country code, e.g. US"},
                    "advertiser_contains": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ad",
            "description": "Fetch one ad with full details including AI summary, rewrites, embeddings status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "ad_id": {"type": "string"},
                },
                "required": ["platform", "ad_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_advertisers",
            "description": "Top advertisers by ad count, with average winner_score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_destinations",
            "description": "Top destination domains across all resolved ads. Pass affiliate_only=true to filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                    "affiliate_only": {"type": "boolean"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hook_breakdown",
            "description": "Distribution of hook archetypes across ads.",
            "parameters": {
                "type": "object",
                "properties": {"platform": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "similar_ads",
            "description": "Find nearest-neighbour ads by copy or image embedding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "ad_id": {"type": "string"},
                    "by": {"type": "string", "enum": ["copy", "image"]},
                    "limit": {"type": "integer"},
                },
                "required": ["platform", "ad_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_competitors",
            "description": "List tracked competitors with their FB page, tech stack, tags.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
    },
]


SYSTEM_PROMPT = """You are an analyst for an internal ad intelligence database.
You answer questions about ads scraped from Meta, TikTok, and other platforms.

Rules:
- Use the available tools to look up real data. Never invent ads, advertisers,
  domains, or scores.
- When the user asks about "winners", "best", "top", or "performing", default to
  filtering by min_score >= 60 unless they say otherwise.
- Keep responses short and dense — bullet points for lists, never wall-of-text.
- When citing an ad, include platform + ad_id so the user can open the dashboard.
- For comparisons or rankings, use top_advertisers / hook_breakdown /
  top_destinations rather than enumerating ads one by one.
- If you don't have enough data to answer, say so plainly — don't speculate.
"""


@dataclass
class AgentReply:
    text: str
    tool_calls: list[dict[str, Any]]
    latency_ms: int


def chat(messages: list[dict[str, str]], max_steps: int = 4) -> AgentReply:
    """Run a chat turn. `messages` is a list of {role, content} dicts."""
    import time

    settings = get_settings()
    key = settings.groq_api_key.get_secret_value()
    if not key:
        raise AdspyError("GROQ_API_KEY not configured")

    try:
        from groq import Groq
    except ImportError as exc:
        raise AdspyError("groq package missing") from exc

    client = Groq(api_key=key)
    history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
    tool_log: list[dict[str, Any]] = []
    t0 = time.time()
    final_text = ""

    for step in range(max_steps):
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history,
            tools=TOOL_SPECS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=1500,
        )
        choice = resp.choices[0]
        msg = choice.message

        # Append the assistant message — may contain content AND tool_calls
        assistant_entry: dict[str, Any] = {"role": "assistant"}
        if msg.content:
            assistant_entry["content"] = msg.content
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        history.append(assistant_entry)

        if not msg.tool_calls:
            final_text = msg.content or ""
            break

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            fn = TOOLS.get(name)
            if fn is None:
                result: Any = {"error": f"unknown tool '{name}'"}
            else:
                try:
                    result = fn(**args)
                except TypeError as exc:
                    result = {"error": f"bad arguments: {exc}"}
                except Exception as exc:  # noqa: BLE001
                    log.error("agent_tool_failed", tool=name, error=str(exc))
                    result = {"error": str(exc)}
            tool_log.append({"name": name, "args": args, "result_len": len(json.dumps(result))})
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": json.dumps(result, default=str)[:8000],
                }
            )

    latency = int((time.time() - t0) * 1000)
    return AgentReply(text=final_text, tool_calls=tool_log, latency_ms=latency)
