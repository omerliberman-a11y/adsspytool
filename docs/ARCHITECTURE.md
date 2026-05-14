# Architecture (zero-cost edition)

See [CLAUDE.md](../CLAUDE.md) for the schema, scoring formula, and conventions. This file is the visual + dependency reference.

## Data flow

```
┌─────────────────────┐   ScrapeQuery     ┌──────────────────────┐
│ CLI / API / worker  │ ───────────────►  │ scrapers/meta        │
└─────────────────────┘                   │ MetaScraper.scrape() │
                                          └──────────┬───────────┘
                                                     │
                              wrap in ScrapeRunner ──┤  (records `scrape_runs` row)
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ MetaGraphClient      │  HTTPS to graph.facebook.com
                                          │ /ads_archive         │
                                          └──────────┬───────────┘
                                                     │
                                       (Phase 1)     │
                            for fields the API hides ▼
                                          ┌──────────────────────┐
                                          │ snapshot_replay      │  Playwright capture once,
                                          │                      │  httpx replay forever after
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ normalize/meta       │ → unified Ad schema
                                          │   on failure ────────┼──► normalize/llm_fallback
                                          │                      │     (Groq/Gemini/Ollama via AIRouter)
                                          └──────────┬───────────┘     writes normalization_failures
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ analyzers/scoring    │ → winner_score (pure)
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ services/ingestion   │ → upsert into Postgres
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ ai/router  (Phase 3) │ → ai_hook, ai_angle, ai_summary,
                                          │ Gemini / Groq /      │   copy_embedding, image_embedding
                                          │ CFWAI / Ollama       │   (cost-aware fallback chain)
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ FastAPI /ads         │ → dashboard (Phase 4)
                                          └──────────────────────┘
```

## Process model

- **API process** — `uvicorn adspy.api.app:app`. Reads. Stateless.
- **Worker process** — `python -m adspy.queue.worker` (Phase 1.5). Pulls jobs from `task_queue` via `SELECT ... FOR UPDATE SKIP LOCKED`. No Redis, no Celery.
- **CLI** — `adspy …`. Same code paths as worker; useful for manual runs.

## Why Graph API (not third-party scrapers)

1. **Free + official** — no per-1k-ad cost, no anti-bot dance, no scraper-churn maintenance.
2. **More fields** — the public API exposes `eu_total_reach`, `delivery_by_region`, `demographic_distribution`, `estimated_audience_size` that most third-party scrapers don't surface.
3. **Stability** — Meta maintains the API contract; third-party scrapers break every few months when Meta changes their internal markup.

The trade-off: the Graph API returns `ad_snapshot_url` instead of direct media URLs. Phase 1 ships a Playwright-based snapshot-replay worker that resolves snapshot URLs to media in bulk, idempotently. Capture happens once (or per session rotation), replay happens for every ad.

## Why an AI router (not a single provider)

We're free-tier-bound, which means every provider has a hard daily ceiling. With four providers chained:

```
text:   groq (30/min, 14.4K/day) → gemini-flash (1.5K/day) → cfwai (10K neurons/day) → ollama (∞ local)
vision: gemini-pro (1.5K/day) → gemini-flash → ollama (llama3.2-vision)
embed:  local BGE → cfwai (free) → fallback to OpenCLIP local
```

…aggregate daily throughput comfortably exceeds 10K AI operations/day, which is more than the scraper layer can produce. The router records every call in `ai_calls` so we can see real consumption per provider per day and tune the chain.

## Dependency graph (allowed imports)

```
   api  ───►  services  ───►  scrapers  ───►  utils, config
    │             │
    │             ├─────►  normalize  ───►  ai (only llm_fallback)
    │             │
    │             ├─────►  analyzers  ───►  (pure: nothing)
    │             │
    │             ├─────►  ai          ───►  utils, config
    │             │
    │             └─────►  models  ───►  db
    │
    └─────────►  models  ───►  db
```

Cycles disallowed. If you find yourself needing one, the right answer is usually:
- a DTO in `scrapers/base.py`, or
- a helper in `utils/`.
