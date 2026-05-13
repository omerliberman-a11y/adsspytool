# Architecture

See [CLAUDE.md](../CLAUDE.md) for the schema, scoring formula, and conventions. This file is the visual + dependency reference.

## Data flow

```
┌─────────────────────┐   ScrapeQuery     ┌──────────────────────┐
│ CLI / API / worker  │ ───────────────►  │ adspy.scrapers/meta  │
└─────────────────────┘                   │ MetaScraper.scrape() │
                                          └──────────┬───────────┘
                                                     │ ApifyRunner
                                                     ▼
                                          ┌──────────────────────┐
                                          │ Apify actor          │
                                          │ apify/facebook-ads-* │
                                          └──────────┬───────────┘
                                                     │ dataset items (raw JSON)
                                                     ▼
                                          ┌──────────────────────┐
                                          │ normalize_meta_ad    │ -> unified ad schema
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ analyzers.scoring    │ -> winner_score
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ services.ingestion   │ -> upsert into Postgres
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │ FastAPI /ads         │ -> dashboard (Phase 4)
                                          └──────────────────────┘
```

## Dependency graph (allowed imports)

```
   api  ───►  services  ───►  scrapers  ───►  utils, config
    │             │
    │             └─────►  analyzers  ───►  (pure: nothing)
    │             │
    │             └─────►  models  ───►  db
    │
    └─────────►  models  ───►  db
```

Cycles are not allowed. If you find yourself needing one, the right answer is usually:
- a DTO in `scrapers/base.py` (e.g., `ScrapeQuery`), or
- a new helper in `utils/`.

## Process model

- **API process** — `uvicorn adspy.api.app:app` — reads. Stateless. Behind a single-user dashboard for now.
- **Worker process** — `celery -A adspy.workers.app worker` — writes. Long Apify calls + AI calls go here, never inline in API handlers.
- **CLI** — `adspy …` — same code paths as worker. Useful for manual scrapes during dev.

## Why Apify (and not custom scrapers)

The Meta Ad Library has aggressive anti-bot. Apify actors keep up with Meta's churn — paying ~\$1.50 per 1,000 ads is far cheaper than maintaining our own scraper. Cap per run via `APIFY_MAX_USD_PER_RUN` (default \$5).

If/when we outgrow Apify on cost, the seam is `ApifyRunner`: replace it with a different transport that yields the same dataset shape, normalizers don't need to change.
