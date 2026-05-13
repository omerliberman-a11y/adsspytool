# Changelog

## [0.1.0] - 2026-05-13
### Added
- Phase 0 scaffold: repo layout, Poetry config, docker-compose (Postgres + pgvector, Redis), Makefile.
- Unified ad schema + `Ad` and `ApifyRun` SQLAlchemy models.
- Alembic with initial migration.
- `ApifyRunner` with retry, cost cap, and run-record persistence.
- Meta scraper + normalizer (defensive against camelCase/snake_case field drift).
- Pure-function winner scoring with longevity / variant / reach / placement / recency components.
- Ingestion service: scrape → normalize → score → upsert.
- FastAPI app with `/health`, `/ads`, `/ads/{platform}/{ad_id}`.
- Typer CLI: `adspy scrape meta` and `adspy ads list`.
- Celery app + `scrape_meta` task.
- Tests: scoring (full coverage of all components), meta normalizer.
- Docs: `CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `apify_actors.md`.

### Stubs (filled in by phases 5–6)
- `adspy/scrapers/x/`, `tiktok/`, `google_ads/`, `linkedin/` — empty packages with phase notes.
