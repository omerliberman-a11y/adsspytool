# Free data sources

The scraping layer is built entirely on **free, public endpoints**. No Apify, no paid scraping SaaS. Each source has a primary path (cheap, structured) and a fallback (Playwright capture-replay for fields the primary misses).

## Meta (Facebook / Instagram / Messenger / Threads)

**Primary**: Meta Ad Library Graph API — `https://graph.facebook.com/v21.0/ads_archive`

- Required: a Facebook Developer App + a User Access Token with `ads_read` scope, **or** a System User Token. Both free.
- Token-creation guide: developers.facebook.com → Apps → My App → Add product "Marketing API" → Tools → Access Token Tool.
- Required params: `ad_reached_countries`, `ad_active_status`, `ad_type=ALL`, and either `search_terms` or `search_page_ids`.
- Useful fields: `ad_creative_bodies`, `ad_creative_link_titles`, `ad_creative_link_descriptions`, `ad_delivery_start_time`, `ad_delivery_stop_time`, `ad_snapshot_url`, `bylines`, `currency`, `delivery_by_region`, `demographic_distribution`, `estimated_audience_size`, `eu_total_reach`, `impressions`, `languages`, `page_id`, `page_name`, `publisher_platforms`, `spend`, `target_ages`, `target_gender`, `target_locations`.
- Pagination: `data` + `paging.cursors.after` + `paging.next`.
- Rate limit: standard Graph API per-app + per-user. Comfortable at our volume.

**Fallback**: Playwright snapshot-replay against `ad_snapshot_url`. The public API does not return:
- Direct video URLs (we get a snapshot URL that hosts the rendered video)
- Hi-res image URLs
- Carousel variant ordering with per-card CTAs

For these we capture the rendered snapshot page once, intercept network XHRs to capture media URLs, then store. Idempotent — we only do this for ads we don't already have a full media record for.

## X (Twitter)

**Primary**: X Ad Transparency CSV — `https://transparency.x.com/en/ads/` (downloads CSV per period). EU coverage only.

**Secondary**: X API free tier — 1.5K tweet reads / month. Used to enrich the CSV with engagement metrics on detected promoted-tweet IDs.

**Tertiary**: Capture-replay against `business.x.com/en/help/ads-business/transparency` GraphQL.

## TikTok

**Primary**: TikTok Creative Center top-ads endpoint — `https://ads.tiktok.com/creative_radar_api/v1/top_ads/v2/list` (public, no auth).

**Fallback**: Capture-replay against `creativecenter.tiktok.com/topads` web UI (needed for hidden filters: industry vertical, format).

## Google

**Primary**: Google Ads Transparency Center RPC — `https://adstransparency.google.com/anji/_/rpc/SearchService/SearchCreatives`.

Pass a JSON-encoded RPC body; returns ad metadata (advertiser, creative IDs, regions, first/last shown). Cookie-session capture once to get the right `x-goog-` headers; then replay.

## LinkedIn

**Primary**: LinkedIn Ad Library API — `https://www.linkedin.com/ad-library/api/search`. Session cookie required. Only meaningful for B2B niches.

## Operational notes

- **One session per platform** is captured ahead of time via `python -m adspy.scrapers.capture_replay capture --platform meta` (interactive Playwright session — log in once, save cookies + headers).
- **Sessions rotate** roughly weekly; the runner detects 401/403 and pages the operator.
- **No Cloudflare/Datadome anti-bot is encountered** on any of the above primary endpoints — they're all official transparency endpoints. The stealth machinery exists in `capture_replay.py` for edge cases only.
- **Volume sanity**: even at 5K ads/day across all platforms, we stay below every free limit. The bottleneck is the AI analysis layer (Phase 3), which is also free-tier but more constrained — see `docs/PLAN.md` budget map.
