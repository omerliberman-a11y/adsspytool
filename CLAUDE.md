# adspy — internal ad intelligence tool (zero-cost architecture)

This file is the **single source of truth** for the architecture, schema, and conventions of this repo. Read it before making changes; update it in the same PR when architecture changes.

## What this is

In-house ad spy tool. We pull public ad libraries (Meta, X, TikTok, Google, LinkedIn), normalize them into one schema, score "winners," run AI analysis on creatives, and surface everything in a dashboard. Goal: out-deliver Foreplay / AdSpy / BigSpy on features they don't have (semantic search, funnel intelligence, temporal diffs, generation loop).

We are the only users. No multi-tenant. No per-user auth.

## Operating constraint: **$0 / month**

This is a hard constraint, not a target. Every component must run on free tiers or open-source. If a feature requires paid infrastructure, surface the trade-off explicitly — do not silently introduce billing.

| Layer | Choice | Why |
|---|---|---|
| Meta ads source | **Graph API `/ads_archive`** (free, official) | More fields than third-party scrapers, no anti-bot dance, no $/k-ad cost |
| Fields Graph API doesn't expose | **Playwright capture-replay** of `ad_snapshot_url` | One-time HAR capture → headless GraphQL replay via httpx |
| X / TikTok / Google / LinkedIn | Public transparency endpoints + capture-replay | All have free internal JSON endpoints |
| Storage | **Postgres + pgvector** self-hosted via Docker | Free; pgvector handles embeddings without Qdrant |
| Object storage | **Cloudflare R2** free tier (10 GB, zero egress) | S3-compatible; egress is what kills budgets, R2 has none |
| Queue | **Postgres `FOR UPDATE SKIP LOCKED`** | Removes Redis + Celery as separate services |
| Scheduling | APScheduler in-process **or** GitHub Actions cron | Both free |
| Vision + video AI | **Google AI Studio (Gemini 2.5 Pro/Flash)** free tier — 1,500 req/day Pro, more on Flash, ingests video URLs natively | Multimodal, no transcription step needed |
| Text AI (rewrite, structured extraction) | **Groq** free tier — Llama 3.3 70B / Qwen 2.5 72B, ~30 req/min | Fastest free inference available |
| Embeddings | **Open weights** (BGE / Nomic / Jina) run locally **or** Cloudflare Workers AI free | No per-call cost |
| Local fallback / offline | **Ollama** with `qwen2.5:14b` or `llama3.3:8b` | Full air-gap capability |
| External access | **Cloudflare Tunnel** | Exposes local API publicly with no VPS, no router config |

## Architecture (one-screen view)

```
search job (keyword | page_id | country)
        │
        ▼
   scrapers/*  ── via free endpoints ──► raw JSON
   ├─ meta/graph_client    (Meta Ad Library Graph API)
   ├─ meta/snapshot_replay (Playwright capture-replay for media URLs)
   └─ {x, tiktok, google_ads, linkedin}/   (capture-replay each)
        │
        ▼
   normalize/* ──► unified Ad schema
   └─ on failure → normalize/llm_fallback (Groq Llama → re-extract from raw_json)
        │
        ▼
   analyzers/scoring → winner_score (pure, no I/O)
        │
        ▼
   services/ingestion → upsert into Postgres
        │
        ▼
   ai/*  ──► creative analysis  (Phase 3)
   ├─ gemini  (vision + video, free tier)
   ├─ groq    (text rewrite + playbook extraction)
   ├─ ollama  (local fallback)
   └─ router  (cost-aware: try free → fallback → local)
        │
        ▼
   api  +  ui  (Phase 4)
```

## Unified ad schema

Every ad from every platform must map to this shape. Adding a new platform = writing a normalizer that produces this. **Do not add columns without updating this section and the migration.**

```
ad_id                  text, PK component with platform
platform               enum: meta | x | tiktok | google | linkedin
advertiser_name        text
advertiser_page_id     text
advertiser_url         text
first_seen             timestamptz
last_seen              timestamptz
days_active            int            -- derived: last_seen - first_seen
countries              text[]
languages              text[]
placements             text[]         -- fb_feed, ig_reels, x_timeline, ...
creative_type          enum: video | image | carousel | text
media_urls             text[]         -- source URLs (from snapshot replay)
media_phash            text[]         -- perceptual hashes per media (dedupe across advertisers)
local_media_paths      text[]         -- R2 keys after download
headline               text
primary_text           text
description            text
cta_text               text
cta_url                text
landing_url            text           -- resolved final URL
variant_count          int            -- how many versions of this ad
reach_band             text           -- EU only
impressions_band       text           -- EU only
spend_band             text           -- EU only
winner_score           int            -- 0..100, computed
hook_type              text           -- curiosity | authority | fear | ...
awareness_stage        int            -- Schwartz 1-5
copy_framework         text           -- PAS | AIDA | FAB | 4U | story | RMBC
ai_hook                text
ai_angle               text
ai_offer               text
ai_summary             text
ai_rewritten_copy      text[]
copy_embedding         vector(1024)   -- BGE-large
image_embedding        vector(768)    -- SigLIP / OpenCLIP, on hero frame
raw_json               jsonb          -- always preserve source-of-truth
```

Primary key: `(platform, ad_id)`.

## Winner-detection scoring

Pure function in `adspy/analyzers/scoring.py`. Weights:

- **Longevity (40%)** — `days_active`. >30d likely winner, >90d near-certain.
- **Variant count (25%)** — advertisers only iterate winners.
- **Reach band (20%)** — EU transparency buckets when present.
- **Platform spread (10%)** — placements diversity.
- **Recency bonus (5%)** — emerging winners <14d that already hit other thresholds.

Re-score nightly as `days_active` grows. Function stays pure (no DB calls) for testability.

A second model **`rising_star_score`** (Phase 11) runs only on ads <14 days old, predicting scale-likelihood from velocity signals (variant_count growth, placement spread growth, advertiser track record).

## Repo layout

```
adspy/
├── api/             FastAPI app + routes
├── scrapers/        one subpackage per platform
│   ├── base.py      ScrapeQuery DTO, ScrapeRunner ABC
│   ├── scrape_runner.py    ScrapeRun row writer (replaces apify_runner.py)
│   ├── capture_replay.py   base class for HAR-capture + GraphQL-replay scrapers
│   └── meta/  x/  tiktok/  google_ads/  linkedin/
├── normalize/       per-source normalizers + llm_fallback
├── analyzers/       pure scoring + (later) AI analyzers
├── ai/              free-tier provider clients (gemini, groq, ollama, cfwai) + router
├── services/        ingestion = scrape -> normalize -> upsert -> score
├── queue/           Postgres-backed task queue (SKIP LOCKED)
├── workers/         in-process worker loops (replaces Celery)
├── db/              SQLAlchemy session
├── models/          SQLAlchemy ORM models
├── cli/             `adspy` CLI entry point
├── utils/           logging, errors, hashing (sha256, phash)
└── config.py        Pydantic Settings, single source of env access
migrations/          Alembic
tests/               pytest
docs/                PLAN.md, ARCHITECTURE.md, CHANGELOG.md, free_data_sources.md
```

## Dependency rules

- `api/` depends on `services/`, `models/`, `db/`, `analyzers/`, `ai/`, `utils/`, `config`.
- `services/` depends on `scrapers/`, `normalize/`, `analyzers/`, `ai/`, `models/`, `db/`, `utils/`, `config`.
- `scrapers/` depends on `utils/`, `config`. Not `services/` or `models/` directly — but **may** write to `scrape_runs` via `scrape_runner`.
- `normalize/` is mostly pure. `normalize/llm_fallback.py` depends on `ai/`.
- `analyzers/scoring.py` depends on **nothing in this repo** (pure function).
- `ai/` depends on `utils/`, `config`. Provides a single `AIRouter` other layers use.
- `models/` depends on `db/`. Nothing else.
- Cycles disallowed. If you need one, the right move is a DTO in `scrapers/base.py` or a helper in `utils/`.

## Conventions

- Python 3.12, Poetry, ruff (lint + format), mypy strict.
- Async only at I/O boundaries (Graph API calls, Playwright workers, FastAPI handlers). Business logic stays sync and pure where possible.
- Pydantic Settings reads env exactly once at process start; everything else takes `Settings` via DI.
- Every scrape records a row in `scrape_runs` (source, query, item_count, duration, error) for replay and observability.
- Upserts keyed on `(platform, ad_id)`. Never insert without `on_conflict`.
- **No paid SaaS without escalation.** If a phase requires it, write up the trade-off in `docs/CHANGELOG.md` and wait for explicit approval.
- Tests for pure logic (`analyzers/`, normalizers) mandatory. Integration tests (DB, Graph API live calls) gated behind `RUN_LIVE_TESTS=1`.
- No logging of secrets. `config.py` masks them in `__repr__`.

## AI provider routing (`adspy/ai/router.py`)

Single entrypoint: `AIRouter.analyze(prompt, *, modality)` where modality ∈ {text, image, video, embedding}. The router tries providers in cost-aware order:

1. **Local (free, slow)** — only if `LOCAL_ONLY=1` or upstream rate-limited.
2. **Cloudflare Workers AI** — free, generous, good for embeddings.
3. **Groq** — free, fastest text. Text/structured-extraction default.
4. **Gemini AI Studio** — free, multimodal. Vision + video default.
5. **Ollama (local)** — final fallback when everything upstream rate-limits.

The router records per-call cost (= 0 for free tiers; tracked anyway for budget alarms) and provider in an `ai_calls` table. If aggregate free-tier consumption approaches a known limit, the router proactively shifts traffic to Ollama.

## When you (Claude Code) make a change

1. Read this file. If your change contradicts it, update this file in the same PR.
2. One phase per PR. Don't bundle.
3. Update `docs/CHANGELOG.md` with one line.
4. Run `make check` (ruff + mypy + pytest) before declaring done.
5. Never weaken the schema. Adding columns is fine; renaming/removing requires a migration and a normalizer review.
6. Never introduce a paid dependency without explicit approval.
