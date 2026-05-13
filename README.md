# adspy

Internal ad intelligence tool. Scrapes Meta / X / TikTok / Google / LinkedIn ad libraries, normalizes them into one schema, scores winners, and surfaces them in a dashboard.

For architecture, schema, and conventions see [CLAUDE.md](CLAUDE.md). For the phased build plan see [docs/PLAN.md](docs/PLAN.md).

## Quickstart

```powershell
# 1. Install deps
poetry install

# 2. Copy env and fill in APIFY_TOKEN + anything else you need
copy .env.example .env

# 3. Start Postgres + Redis
make up

# 4. Run migrations
make migrate

# 5. Hit it with the CLI
poetry run adspy scrape meta --keyword "cold plunge" --country US
poetry run adspy ads list --min-score 70

# 6. Or start the API
make api
# then GET http://localhost:8000/health
#      GET http://localhost:8000/ads?platform=meta&min_score=70
```

## Tests

```powershell
make check     # ruff + mypy + pytest
poetry run pytest tests/test_scoring.py -v
```

## Project status

Phase 0 (scaffold) shipped. Phase 1 (Meta scraper end-to-end) is next — see [docs/PLAN.md](docs/PLAN.md).
