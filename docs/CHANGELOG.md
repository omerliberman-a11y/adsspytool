# Changelog

## [1.0.2] - 2026-05-14 — Live verified end-to-end on the office machine

System is up and serving with **22 fully-analyzed demo ads** populated entirely from local resources (no external API tokens used).

### Live verification
- All 38/38 pytest cases pass (scoring + meta normalizer + AI router).
- Postgres running on :5434 (5433 was occupied), Next.js on :3001 (3000 was occupied).
- Worker drained **43 tasks** (21 analyze + 22 embed) with `done` status.
- AI analysis routed entirely through **Ollama** (`qwen2.5:14b`) with `LOCAL_ONLY=true` — 22 calls logged in `ai_calls`. Real hook-types extracted: `problem_agitation` (8), `contrarian` (5), `curiosity` (3), `before_after` (3), `transformation` (2), `authority` (1).
- Copy embeddings via local BGE-large on all 22 ads, image embeddings skipped (no URLs).
- `/similar/{platform}/{ad_id}?by=copy` returns real pgvector cosine distances — first cold-plunge anchor pulls 3 other cold-plunge ads as top-3 nearest neighbors.
- Daily snapshot wrote 22 `ad_history` rows for 2026-05-14.
- Rip-off scan found the 1 seeded cross-advertiser pHash cluster.
- All 11 endpoints (6 API, 5 dashboard) return HTTP 200.

### Fixes
- API `/ads/{platform}/{ad_id}` serializer was missing `hook_type`, `awareness_stage`, `copy_framework`, `ai_offer`, `ai_rewritten_copy`, `rising_star_score`. Added.
- `scripts/seed_demo.py` — 22 realistic ads across 7 niches, used for offline demo and dev.
- `OLLAMA_TEXT_MODEL` default updated to match common install (`qwen2.5:14b`, no `-instruct` suffix in tag).
- Pinned `typing-inspection`, `torchvision ^0.20` so Python 3.13 installs cleanly.

---

## [1.0.1] - 2026-05-14 — Runtime fixes from live-bringup

- Postgres port 5433→5434 (collision), dashboard port 3000→3001 (collision).
- FastAPI CORS allows both 3000 and 3001 origins.
- `adspy/queue/__main__.py` — package entrypoint so `python -m adspy.queue` doesn't suffer the `__main__`/package double-namespace bug.
- React 19-RC → 19 stable; Next 15.0.3 → 15.1+.

---

## [1.0.0] - 2026-05-14 — Ready for office testing

Complete end-to-end build: Phase 1 through Phase 5 + selected Phase 10 features. Free-tier only.

### Added — Backend
- **Postgres task queue** (`adspy/queue/`) — `SELECT ... FOR UPDATE SKIP LOCKED`. Handler registry + worker loop. Replaces Celery + Redis entirely. Migration `0003` adds the `tasks` table.
- **Snapshot-replay worker** (`adspy/scrapers/meta/snapshot_replay.py`) — Playwright headless, intercepts network XHRs + scrapes DOM images to extract media URLs the Graph API hides. Downloads to R2 (or local fs fallback), computes SHA-256 + pHash. Sets `creative_type` based on actual media.
- **MediaStore** (`adspy/storage/`) — R2 client (S3-compatible, boto3) with local-filesystem fallback for no-config dev.
- **Creative AI analysis** (`adspy/ai/analysis.py`) — for each ad, sends visual to Gemini (image/video), then structured extraction prompt to Groq → fills `hook_type`, `awareness_stage`, `copy_framework`, `ai_hook`, `ai_angle`, `ai_offer`, `ai_summary`, `ai_rewritten_copy[]`. Robust JSON parsing, value cleaning, and `ai_calls` logging per provider call.
- **Embeddings** (`adspy/embeddings/`) — local BGE-large for copy (1024-d), local OpenCLIP ViT-L-14 for image (768-d). Models cache in-process after first load.
- **Daily snapshot worker** (`adspy/services/daily_snapshot.py`) — writes one `ad_history` row per ad per day. Bootstrap for the temporal layer.
- **Cross-advertiser rip-off detection** (`adspy/services/rip_off.py`) — pHash clustering with Hamming threshold 8 to flag visual rip-offs across advertisers.
- **Ingestion auto-chains** — `services/ingestion.py` enqueues `snapshot_replay` + `analyze_ad` + `embed_ad` tasks for every new ad ingested.
- **API completions**:
  - `GET /stats` — totals, AI consumption, tasks by status, breakdowns.
  - `POST /scrape/meta` — enqueue a scrape via API.
  - `GET /tasks`, `GET /tasks/{id}` — live queue view.
  - `GET /similar/{platform}/{ad_id}?by=copy|image` — pgvector cosine distance.
  - `POST /admin/{score/recompute, analyze/batch, embed/batch, snapshot/batch, daily-snapshot, rip-off-scan}`.
- **CLI extensions** (`adspy/cli/main.py`):
  - `adspy queue {worker, status, enqueue}` — queue management.
  - `adspy ai {analyze, embed, daily-snapshot, rip-off-scan}` — analysis batch ops.
  - `adspy ads list --hook curiosity` — filter by hook type.

### Added — Frontend
- **Next.js 15 dashboard** (`dashboard/`) — TypeScript, Tailwind, App Router.
- Pages:
  - `/` — winners card grid + filter bar (platform / creative / hook / score / days / country).
  - `/ads/[platform]/[ad_id]` — detail view with hero media (auto-play on hover for video), AI hook, why-it-works, original copy, 3 rewritten variants, two "more like this" panels (by copy + by image), full metadata sidebar.
  - `/playbooks` — top 4 winners per hook archetype.
  - `/stats` — visual dashboard of platform/hook/creative breakdowns + AI consumption.
  - `/queue` — live task-queue view with 3s refresh (SWR).
  - `/scrape` — form to enqueue a new scrape from the UI.
- Dark theme with semantic colors (good/warn/bad).

### Added — Ops
- **`scripts/bootstrap.ps1`** — one-shot setup. Verifies prereqs, installs Python + Playwright + Node deps, starts Postgres, migrates, prints next-step commands.
- **CORS** on FastAPI for the Next.js dev server.
- **Makefile**: `make worker` runs the queue worker; `make install` now runs `playwright install chromium`.

### Schema
- New: `tasks` table.
- The Ad row gains real data in all the v0.2 columns (`media_phash`, `hook_type`, `awareness_stage`, `copy_framework`, `rising_star_score`, `copy_embedding`, `image_embedding`).

---

## [0.2.0] - 2026-05-14 — Zero-cost re-architecture

Operating constraint changed to $0/month. Removed Apify, Celery, Redis. Added Meta Graph API client, capture-replay base, AI provider package (Gemini/Groq/CFWAI/Ollama) with cost-aware router, last-mile LLM normalizer, four new tables (scrape_runs, normalization_failures, ai_calls, ad_history). See git history for full diff.

## [0.1.0] - 2026-05-13
Phase 0 scaffold: repo layout, Poetry, docker-compose, Alembic, unified Ad schema, pure-function scorer, FastAPI skeleton, Typer CLI, Apify-based Meta scraper (subsequently removed in 0.2).
