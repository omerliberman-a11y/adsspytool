# Changelog

## [0.2.0] - 2026-05-14 — Zero-cost re-architecture

### Constraint
Operating constraint changed to **$0 / month**. All paid SaaS removed.

### Removed
- Apify and the `apify-client` dependency (replaced by Meta Graph API + Playwright capture-replay).
- Celery + Redis (replaced by Postgres `FOR UPDATE SKIP LOCKED` queue, Phase 1.5).
- `adspy/scrapers/apify_runner.py`, `adspy/models/apify_run.py`, the `apify_runs` table, `docs/apify_actors.md`.

### Added
- `adspy/scrapers/meta/graph_client.py` — Meta Ad Library Graph API client with cursor pagination + retry.
- `adspy/scrapers/scrape_runner.py` — generic `ScrapeRunner` context manager that writes one `scrape_runs` row per scrape (source-agnostic).
- `adspy/scrapers/capture_replay.py` — base class for HAR-capture + httpx GraphQL/RPC replay (used by X / TikTok / Google / LinkedIn in later phases).
- `adspy/ai/` — provider clients (Gemini AI Studio, Groq, Cloudflare Workers AI, Ollama) and a cost-aware `AIRouter` that falls through on rate-limit/outage.
- `adspy/normalize/` — package for per-platform normalizers (decoupled from `scrapers/`).
- `adspy/normalize/llm_fallback.py` — last-mile LLM normalizer that recovers unparseable records via the AI router and logs to `normalization_failures` for offline patching.
- New tables: `scrape_runs`, `normalization_failures`, `ai_calls`, `ad_history`.
- New ad fields: `media_phash`, `hook_type`, `awareness_stage`, `copy_framework`, `rising_star_score`, `copy_embedding` (pgvector 1024), `image_embedding` (pgvector 768).
- `docs/free_data_sources.md` — endpoint catalog per platform.
- `tests/test_ai_router.py` — offline tests for provider-selection logic.

### Changed
- `adspy/normalize/meta.py` is the Graph-API-shaped normalizer; the old camelCase-aware version under `adspy/scrapers/meta/normalizer.py` is gone.
- `Ad` model: added new columns above. Migration `0002` handles the upgrade.
- `MetaScraper` now yields raw items directly (no more `(run, items)` tuple); the `ScrapeRunner` context manager writes the run record transparently.
- `IngestionResult` has a `recovered` count (rows the classic normalizer couldn't parse but the LLM fallback rescued).
- `docker-compose.yml`: dropped Redis (no Celery).
- `Makefile`: added `make capture platform=<name>` for capture-replay session bootstrap; `make install` also runs `playwright install chromium`.

### Free-tier budget map
Documented in `docs/PLAN.md`. Soft caps in `Settings` (`SCRAPE_MAX_ITEMS_PER_RUN`, etc.) keep runs from accidentally bursting limits.

---

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
