# adspy

Internal ad intelligence tool. Scrapes Meta / X / TikTok / Google / LinkedIn ad libraries, normalizes them into one schema, scores winners, runs free-tier AI analysis on creatives, generates rewritten copy variants, and surfaces everything in a Next.js dashboard with semantic "more like this" search.

**Operating constraint: zero monthly cost.** Built entirely on free APIs and open-source. See [CLAUDE.md](CLAUDE.md) for architecture and [docs/PLAN.md](docs/PLAN.md) for the phased build plan.

## Quickstart — one command

```powershell
cd E:\adsspytool
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

The bootstrap script:
1. Verifies python ≥ 3.12, poetry, docker, node, npm.
2. Creates `.env` from `.env.example` if missing.
3. `poetry install` + `playwright install chromium`.
4. Starts Postgres + pgvector via Docker.
5. Runs migrations (0001 → 0003).
6. Installs the Next.js dashboard deps.
7. Prints the three commands to run (API, worker, dashboard).

Then fill in `.env`:

```env
META_GRAPH_TOKEN=     # developers.facebook.com → Tools → Access Token Tool (scope: ads_read)
GEMINI_API_KEY=       # aistudio.google.com → Get API Key
GROQ_API_KEY=         # console.groq.com/keys
# CF_ACCOUNT_ID / CF_API_TOKEN — optional (embeddings via Cloudflare Workers AI)
# R2_*                — optional (Cloudflare R2 media storage; local fs fallback otherwise)
```

…and run the three processes:

```powershell
# Terminal 1 — API
make api                # http://localhost:8000  /docs

# Terminal 2 — Worker (consumes the queue)
make worker

# Terminal 3 — Dashboard
cd dashboard
npm run dev             # http://localhost:3000
```

## What you can do

### From the dashboard (http://localhost:3000)
- **Winners** — card grid of every ad sorted by `winner_score`. Filter by platform / creative type / hook / country / min score / days active.
- **Playbooks** — top 4 winners per hook archetype across the whole DB.
- **Stats** — totals, AI-call consumption today (so you can see free-tier headroom), tasks by status.
- **Queue** — live view of the task queue, 3s refresh.
- **New scrape** — submit a keyword/page job; worker picks it up and chains snapshot-replay → analysis → embedding.
- **Ad detail** — hero media, AI hook, why-it-works summary, original copy, 3 AI-rewritten variants, full metadata sidebar, and **two "more like this" panels** (semantic by copy, visual by image).

### From the CLI
```powershell
poetry run adspy scrape meta --keyword "cold plunge" --country US --limit 50
poetry run adspy ads list --min-score 70 --hook curiosity
poetry run adspy ai analyze                    # batch-analyze ads missing ai_summary
poetry run adspy ai embed                      # batch-embed ads missing copy_embedding
poetry run adspy ai daily-snapshot             # write today's ad_history rows
poetry run adspy ai rip-off-scan               # cross-advertiser pHash dedup
poetry run adspy queue worker                  # foreground worker
poetry run adspy queue status                  # task counts by status
```

### From the API
```
GET  /health
GET  /ads?platform=meta&min_score=70&hook_type=curiosity&country=US
GET  /ads/{platform}/{ad_id}
GET  /similar/{platform}/{ad_id}?by=copy   # or by=image
GET  /stats
GET  /tasks?status=running
POST /scrape/meta                          # enqueue a scrape
POST /admin/score/recompute
POST /admin/analyze/batch?limit=100
POST /admin/embed/batch?limit=200
POST /admin/snapshot/batch?limit=100
POST /admin/daily-snapshot
POST /admin/rip-off-scan
```

Auto-generated docs at `http://localhost:8000/docs`.

## Architecture

```
search job ─► MetaScraper ─► Graph API ─► raw JSON
                                            │
                            normalize/meta ─┤  on failure ─► llm_fallback (Groq)
                                            ▼
                                   unified Ad schema
                                            │
                       analyzers/scoring  ──┤  pure → winner_score
                                            ▼
                       services/ingestion  ─┤  upsert + enqueue followups
                                            ▼
                                ┌───────────┴───────────┐
                                ▼                       ▼
                         queue/snapshot_replay   queue/analyze_ad ─► ai/router
                         (Playwright media)      queue/embed_ad   ─► BGE + CLIP local
                                ▼                       ▼
                                └───► Postgres + pgvector ◄───┘
                                            │
                                            ▼
                                   FastAPI  +  Next.js
```

Full detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Free-tier budget map in [docs/PLAN.md](docs/PLAN.md).

## Free stack

| Layer | Service | Free tier |
|---|---|---|
| Meta ads | Meta Graph API (`/ads_archive`) | Standard Graph rate limits |
| Other platforms | Capture-replay (Playwright once, httpx forever) | Free, infinite |
| Vision + video | Google AI Studio (Gemini 2.5 Pro/Flash) | 1,500 req/day Pro |
| Text AI | Groq (Llama 3.3 70B) | ~30 req/min, 14.4K req/day |
| Embeddings (copy) | BGE-large local | Free, ~1.3 GB on disk |
| Embeddings (image) | OpenCLIP ViT-L-14 local | Free, ~890 MB |
| Storage | Postgres + pgvector self-hosted | Free |
| Media | Cloudflare R2 (optional) / local fs | 10 GB free, zero egress |

## Tests

```powershell
make check     # ruff + mypy + pytest
poetry run pytest tests/test_scoring.py -v
```

## Project status

- **Phase 0** — Scaffold ✅
- **Phase 0.5** — Zero-cost re-architecture ✅
- **Phase 1** — Meta Graph + snapshot replay ✅
- **Phase 1.5** — Postgres task queue + worker ✅
- **Phase 2** — Scoring API + stats ✅
- **Phase 3** — Creative AI analysis (Gemini + Groq + Ollama fallback) ✅
- **Phase 4** — Embeddings + similarity API ✅
- **Phase 5** — Next.js dashboard ✅
- **Phase 10 preview** — Daily ad_history snapshot + rip-off detection ✅

Remaining (next sessions):
- Phase 6 — X scraper
- Phase 7 — TikTok / Google / LinkedIn
- Phase 8 — Funnel intelligence (landing-page render + offer + tech-stack)
- Phase 9 — Playbook extraction expansion
- Phase 10 — Full temporal layer (launch radar, heating-up, rising-star model)
- Phase 11 — Conversational agent
- Phase 12 — Generation loop (briefs, storyboards)
