# Build plan

The v1 plan is Phases 0–7 (Foreplay-parity). Phases 8–15 are the "super tool" extensions that take us past competitors. One phase per PR.

## v1 (Foreplay parity)

### Phase 0 — Scaffold ✅
Repo layout, Postgres + Alembic + initial migration, FastAPI skeleton, Apify wrapper, env config, Docker compose, CLI entry point, scorer + tests. **This commit.**

### Phase 1 — Meta scraper end-to-end (1–2 days)
- Wire `MetaScraper` to live `apify/facebook-ads-scraper`
- Verify normalizer against ≥3 real keyword runs and ≥3 page-id runs
- Tune `_extract_media` and `_detect_creative_type` against real field drift
- Add integration test that hits the live actor with `--limit 5` behind an env flag
- **Done when:** `adspy scrape meta --keyword "cold plunge"` ingests ≥50 ads with zero `errors`

### Phase 2 — Scoring API (½ day)
- Implement filters on `GET /ads` (already scaffolded; verify all paths)
- Add `GET /stats` (counts per platform / creative_type / score band)
- Add `POST /score/recompute` to re-score all rows after a weight change
- **Done when:** Dashboard mockups can be fed real data

### Phase 3 — Creative download + AI analysis (1–2 days)
- R2 client, media-download Celery task per ad
- Image → Claude vision (hook / angle / offer / framework)
- Video → Gemini 2.5 Pro (multimodal, ingests video URL directly)
- Text-only → Claude (same fields)
- Generate 3 rewritten copy variants per ad in our brand voice
- **Done when:** Every newly-ingested ad has `ai_*` fields populated within 5 min of scrape

### Phase 4 — Dashboard (2 days)
- Next.js + Tailwind, card grid, filter sidebar, detail view
- Save-to-swipe-file, CSV/JSON export
- **Done when:** Team uses it daily instead of Meta Ad Library

### Phase 5 — X (1 day)
- `xtdata/twitter-x-scraper` for promoted-tweet detection
- `business.x.com` transparency CSV ingest (EU)
- X normalizer maps into the unified schema
- **Set expectation:** X transparency data is thinner than Meta — adjust scoring weights for X (less reach signal, more engagement weight)

### Phase 6 — TikTok / Google / LinkedIn (1 day each)
- One scraper module + normalizer per platform
- Pipeline downstream is unchanged

### Phase 7 — Scheduling + alerts (½ day)
- Saved searches with nightly Celery beat
- Slack/email alert on new ads above a threshold

## "Super tool" extensions

### Phase 8 — Funnel intelligence (~3 days)
Playwright workers render every CTA's landing page. Extract offer (price, bumps, guarantee, urgency), fingerprint tech stack (Wappalyzer-style), detect affiliate networks, scrape Shopify product data when detected. Re-fetch landing pages weekly to diff offer changes.

### Phase 9 — Embeddings + semantic search (~2 days)
pgvector. Image embeddings (SigLIP/OpenCLIP), copy embeddings, video keyframe embeddings + audio transcript. "More like this", reverse image search, near-dup detection.

### Phase 10 — Playbook extraction (~1.5 days)
Structured tactic fields per ad: hook type, angle, promise, mechanism, proof element, offer type, framework. Faceted browse + Playbook view.

### Phase 11 — Temporal layer (~3 days)
Daily snapshots, advertiser diff jobs, launch radar (new advertisers in niche), heating-up dashboard, rising-star score for <14d ads.

### Phase 12 — Conversational agent (~1.5 days)
Claude + tool-use over our Postgres + pgvector + S3. Same tools the dashboard uses.

### Phase 13 — Generation loop (~2 days)
Variant generator, storyboard generator (for video winners), brief generator. Brand-voice config per project.

### Phase 14 — Adjacent intelligence (~1 week, parallelizable)
TikTok organic-creator spy, ClickBank/Digistore24 leaderboard ingest, domain monitor, email-sequence capture.

### Phase 15 — Workflow layer (~3 days)
Tags, folders, swipe boards, share-links, Notion/Airtable/Slack export, scheduled digest emails.
