# Build plan — zero-cost edition

Replaces the original Apify-based v1. All paid SaaS removed. Phases re-ordered to bring funnel intelligence + temporal layer + embeddings into v1 (they're cheap once the right primitives exist) and to ship a usable dashboard sooner.

## v1 (Foreplay-parity + the unique edges, all free)

### Phase 0 — Scaffold ✅
Repo layout, Postgres + Alembic migration, FastAPI skeleton, env config, Docker compose, CLI entry point, scorer + tests.

### Phase 0.5 — Zero-cost re-architecture ← *this PR*
- Remove `apify-client` dependency
- New `adspy/scrapers/meta/graph_client.py` — Meta Ad Library Graph API client
- New `adspy/scrapers/capture_replay.py` — Playwright HAR-capture + httpx replay base
- Rename `apify_runner.py` → `scrape_runner.py`, `ApifyRun` → `ScrapeRun`
- New `adspy/ai/` package — Gemini, Groq, Ollama, Cloudflare WAI clients + cost-aware router
- New `adspy/normalize/llm_fallback.py` — last-mile LLM normalizer
- New `adspy/queue/` — Postgres `SKIP LOCKED` task queue (will replace Celery in Phase 1.5)
- Migration `0002` — rename `apify_runs` → `scrape_runs`, add `normalization_failures`, add `ai_calls`, add `ad_history`

### Phase 1 — Meta scraper end-to-end via Graph API (1–2 days)
- Live calls to `graph.facebook.com/v21.0/ads_archive` with cursor pagination
- Verify normalizer against ≥3 keyword queries and ≥3 page_id queries
- Add snapshot-replay worker that hits `ad_snapshot_url` via Playwright to extract media URLs the public API hides (video URLs, hi-res images)
- Compute pHash + SHA-256 per media file at ingestion
- Done when: `adspy scrape meta --keyword "cold plunge" --country US` ingests ≥50 ads with `media_urls` populated and `errors=0`

### Phase 2 — Scoring + API + saved searches (½ day)
- Filters on `GET /ads` (already scaffolded; complete + tested)
- `GET /stats` (counts per platform / creative_type / score band)
- `POST /score/recompute` (re-score all rows; needed after weight tuning)
- Saved searches stored in `searches` table

### Phase 3 — Creative AI analysis via free tiers (1–2 days)
- R2 client, media-download worker per new ad
- `ai/router.py` picks provider per modality (Gemini for image/video, Groq for text)
- For each ad: extract `hook_type`, `awareness_stage`, `ai_angle`, `ai_offer`, `copy_framework`, `ai_summary` + 3 rewritten copy variants
- For video: Gemini ingests the URL directly (no transcription step in v1)
- Done when: every newly-ingested ad has `ai_*` fields populated within 5 min of scrape

### Phase 4 — Embeddings + semantic search (1 day)
- `image_embedding` via local SigLIP / OpenCLIP; `copy_embedding` via local BGE-large
- pgvector HNSW index
- API: `GET /ads/similar/{platform}/{ad_id}` (image + copy similarity)
- "More like this" + reverse-image search powered for free

### Phase 5 — Dashboard (2 days)
- Next.js + Tailwind, card grid, filter sidebar, detail view
- "More like this", "Save to swipe file", CSV/JSON export
- Single-user, no auth

### Phase 6 — X (1 day)
- Capture-replay against X Ad Transparency CSV (EU) + promoted-tweet detection via X API free tier (1.5K tweets/month)
- X normalizer maps into unified schema
- Expectation: X transparency is thinner — weight scoring more heavily on engagement + variant count

### Phase 7 — TikTok / Google / LinkedIn (~1 day each)
- TikTok: `creative_radar_api/v1/top_ads/v2/list` endpoint (no auth, returns JSON)
- Google: `adstransparency.google.com/anji/_/rpc` (public RPC)
- LinkedIn: ad-library API (cookie-session capture-replay)

### Phase 8 — Funnel intelligence (~3 days) — *brought forward from "super tool"*
- Playwright workers render every CTA's landing page
- Offer extraction (price, bumps, guarantee, urgency) via Gemini vision on full-page screenshot
- Tech-stack fingerprint (Wappalyzer rules + Webpack chunk-hashes)
- Affiliate-network detection (ClickBank, Digistore24, MaxBounty, BuyGoods, WarriorPlus signatures)
- Shopify product scrape when detected
- Re-fetch landing pages weekly → diff for offer changes

### Phase 9 — Playbook extraction (~1.5 days)
- Structured tactic fields per ad: `hook_type`, `angle`, `promise`, `mechanism`, `proof_type`, `offer_type`, `framework`, `cta_pattern`, `awareness_stage`
- Faceted browse in the dashboard
- Standalone "Playbook" view: top N hooks per niche per N days

### Phase 10 — Temporal layer + rising-star (~2 days)
- Daily `ad_history` snapshots per ad (status, days_active, variant_count)
- Advertiser-level diff jobs (what's new today / what got killed)
- Launch radar: new advertisers entering a niche in last 7/30 days
- Heating-up dashboard: ad-volume + spend-band trend per niche
- `rising_star_score` model for ads <14 days old

### Phase 11 — Conversational agent (~1.5 days)
- Claude/Groq with tool-use over our Postgres + pgvector + R2
- Same tools the dashboard uses; agent gets new capabilities for free as we ship features

### Phase 12 — Generation loop (~2 days)
- Variant generator (preserves structural skeleton of a winner)
- Storyboard generator for video winners (Gemini extracts scene beats → shot list)
- Brief generator (full creative brief from N winning ads + product spec)
- Brand-voice config per project

### Phase 13 — Adjacent intelligence (~1 week, parallelizable)
- TikTok organic-creator audio fingerprint match (chromaprint) to find creators using same sound as winning ads
- ClickBank / Digistore24 leaderboard ingest, cross-ref with detected ads
- Domain monitor (backfill every ad an advertiser has run, every landing change)
- Email-sequence capture (signup automation, parse Klaviyo/ActiveCampaign headers)

### Phase 14 — Workflow layer (~3 days)
- Tags, folders, swipe boards
- Share-links (read-only public view per board)
- Notion / Airtable / Slack export
- PDF reports, scheduled digest emails per saved search

## Free-tier budget map (limits to monitor)

| Service | Free limit | Our expected load |
|---|---|---|
| Meta Graph API | ~200 req/hr per token, no hard daily | ~50–200 ads/req × 10 req/scrape = 2K ads/scrape; well within |
| Gemini AI Studio (Pro) | 1.5K req/day | Vision/video on new ads only; ~500–1000/day comfortably |
| Gemini AI Studio (Flash) | 1.5K req/day per project, multiple projects allowed | Light text + image classification, ~few thousand/day |
| Groq | ~30 req/min, 14.4K req/day | Text rewriting; well within for daily volumes |
| Cloudflare Workers AI | 10K neurons/day | Embeddings + auxiliary inference |
| Cloudflare R2 | 10 GB storage, **0 egress** | Media downloads; rotate older media to cold storage |
| Cloudflare Tunnel | unlimited | API exposure |
| GitHub Actions cron | 2K min/month | Daily snapshots + saved-search runs |

If a limit gets close, the `AIRouter` automatically shifts to the next provider in the chain.
