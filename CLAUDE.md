# adspy — internal ad intelligence tool

This file is the **single source of truth** for the architecture, schema, and conventions of this repo. Future Claude Code sessions must read it before making changes and update it when architecture changes.

## What this is

An in-house ad spy tool for the team. We scrape public ad libraries (Meta, X, TikTok, Google, LinkedIn), normalize ads into one schema, score them for "winner" likelihood, run AI analysis over the creatives, and surface everything in a dashboard. The goal is to find the best offers and the best-working creatives faster than off-the-shelf tools (Foreplay / AdSpy / BigSpy).

We are the only users. No multi-tenant, no per-user auth in v1.

## Architecture (one-screen view)

```
search job (keyword | competitor page | country)
        │
        ▼
   scrapers/*  ── via Apify actors ──► raw JSON
        │
        ▼
   normalizer  ──► unified Ad schema
        │
        ▼
   scorer      ──► winner_score (0-100)
        │
        ▼
   storage     ──► Postgres (ads, apify_runs)  +  R2 (media, later)
        │
        ▼
   analyzers   ──► Claude/Gemini  (later phase)
        │
        ▼
   API + UI    ──► FastAPI + Next.js dashboard
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
media_urls             text[]         -- source URLs
local_media_paths      text[]         -- R2/S3 keys after download
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
ai_hook                text           -- later phase
ai_angle               text
ai_offer               text
ai_framework           text
ai_summary             text
ai_rewritten_copy      text[]
raw_json               jsonb          -- always preserve source-of-truth
```

Primary key: `(platform, ad_id)`.

## Winner-detection scoring

Pure function in `adspy/analyzers/scoring.py`. Inputs come from the schema above. Weights:

- **Longevity (40%)** — `days_active`. >30d likely winner, >90d near-certain.
- **Variant count (25%)** — advertisers only iterate winners.
- **Reach band (20%)** — EU transparency buckets when present.
- **Platform spread (10%)** — number of placements (FB + IG + Messenger + Threads etc).
- **Creative recency bonus (5%)** — extra points for <14d-old ads already hitting other thresholds (emerging winners).

Re-score nightly as `days_active` grows. The function must stay pure (no DB calls) for testability.

## Repo layout

```
adspy/
├── api/             FastAPI app + routes
├── scrapers/        one subpackage per platform; all use ApifyRunner
│   ├── base.py      ScrapeQuery DTO
│   ├── apify_runner.py
│   └── meta/  x/  tiktok/  google_ads/  linkedin/
├── analyzers/       pure scoring + (later) AI analyzers
├── services/        ingestion = scrape -> normalize -> upsert -> score
├── workers/         Celery app + tasks
├── db/              SQLAlchemy session
├── models/          SQLAlchemy ORM models
├── cli/             `adspy` CLI entry point
├── utils/           logging, errors
└── config.py        Pydantic Settings, single source of env access
migrations/          Alembic
tests/               pytest
docs/                PLAN.md, ARCHITECTURE.md, CHANGELOG.md, apify_actors.md
```

## Dependency rules

- `api/` may depend on `services/`, `models/`, `db/`, `analyzers/`, `utils/`, `config`.
- `services/` may depend on `scrapers/`, `analyzers/`, `models/`, `db/`, `utils/`, `config`.
- `scrapers/` may depend on `utils/`, `config`. **Not** on `services/` or `models/`.
- `analyzers/scoring.py` depends on **nothing in this repo** (pure function on dicts/dataclasses).
- `models/` may depend on `db/`. Nothing else.
- Cycles are not allowed. If you need to break one, the right move is usually a DTO in `scrapers/base.py` or a new module in `utils/`.

## Conventions

- Python 3.12, Poetry, ruff (lint + format), mypy strict.
- Async only at I/O boundaries (Apify HTTP calls, FastAPI handlers). Business logic stays sync and pure where possible.
- Pydantic Settings reads env exactly once at process start; everything else takes `Settings` via DI.
- Every Apify run records a row in `apify_runs` (cost, duration, dataset id, status) before its dataset is parsed — for cost tracking and replay.
- Upserts are keyed on `(platform, ad_id)`. Never insert without `on_conflict`.
- Tests for pure logic (`analyzers/`, normalizers) are mandatory. Integration tests (DB, Apify) are nice-to-have.
- No logging of secrets. `config.py` masks them in `__repr__`.

## Phases (see docs/PLAN.md for detail)

- **0** scaffold ✅ (this commit)
- **1** Meta scraper end-to-end ← next
- **2** Scoring API
- **3** Creative download + AI analysis
- **4** Dashboard (Next.js)
- **5** X
- **6** TikTok / Google / LinkedIn
- **7** Scheduling + alerts
- **8+** Funnel intel, embeddings, playbooks, temporal layer, agent, generation loop — see PLAN.md

## When you (Claude Code) make a change

1. Read this file. If your change contradicts it, update this file in the same PR.
2. One phase per PR. Don't bundle.
3. Update `docs/CHANGELOG.md` with one line.
4. Run `make check` (ruff + mypy + pytest) before declaring done.
5. Never weaken the schema. Adding columns is fine; renaming/removing requires a migration and a normalizer review.
