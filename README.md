# adspy

Internal ad intelligence tool — scrapes Meta / X / TikTok / Google / LinkedIn ad libraries, normalizes them into one schema, scores winners, runs AI analysis on creatives, and surfaces them in a dashboard.

**Operating constraint: zero monthly cost.** Built entirely on free APIs and open-source. See [CLAUDE.md](CLAUDE.md) for architecture and [docs/PLAN.md](docs/PLAN.md) for the phased build plan.

## Free stack

| Layer | Service | Free tier |
|---|---|---|
| Meta ads | Meta Graph API (`/ads_archive`) | Standard Graph rate limits, plenty |
| Vision + video AI | Google AI Studio (Gemini 2.5) | 1,500 req/day Pro |
| Text AI | Groq (Llama 3.3 70B) | ~30 req/min, 14.4K req/day |
| Embeddings | Cloudflare Workers AI | 10K neurons/day |
| Local fallback | Ollama | Unlimited (your hardware) |
| Storage | Postgres + pgvector (self-hosted) | Free |
| Media | Cloudflare R2 | 10 GB, zero egress |
| External access | Cloudflare Tunnel | Free, no VPS needed |

## Quickstart

```powershell
# 1. Install Python deps + Playwright Chromium
poetry install
poetry run playwright install chromium

# 2. Copy env and fill in free-tier keys
copy .env.example .env
# - META_GRAPH_TOKEN  (developers.facebook.com → Tools → Access Token Tool)
# - GEMINI_API_KEY    (aistudio.google.com → Get API Key)
# - GROQ_API_KEY      (console.groq.com/keys)
# - CF_ACCOUNT_ID / CF_API_TOKEN  (optional, for embeddings)

# 3. Start Postgres
make up

# 4. Migrate
make migrate

# 5. Scrape
poetry run adspy scrape meta --keyword "cold plunge" --country US --limit 50
poetry run adspy ads list --min-score 70

# 6. Or start the API
make api
# GET http://localhost:8000/health
# GET http://localhost:8000/ads?platform=meta&min_score=70
```

## Tests

```powershell
make check     # ruff + mypy + pytest
poetry run pytest tests/test_scoring.py -v
```

## Status

Phase 0.5 (zero-cost re-architecture) shipped. Phase 1 (live Graph API + snapshot replay for media) is next — see [docs/PLAN.md](docs/PLAN.md).
