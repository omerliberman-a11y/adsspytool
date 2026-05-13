# Apify actors — which we use and why

The whole scraping layer is built on Apify so we don't have to maintain anti-bot evasion ourselves. One actor per platform; if it stops working we swap the actor without touching anything downstream.

## Meta — `apify/facebook-ads-scraper` (current)

- Hits the Meta Ad Library directly (FB + IG + Messenger + Threads coverage)
- Accepts `startUrls` of search/keyword/page-view URLs
- Returns structured ad records (text, media URLs, dates, page info, variant counts, EU reach bands when present)
- Cost: ~\$1.50 per 1,000 ads (very cheap)
- **Why this one:** widest field coverage, mature, actively maintained

### Alternative
`scraper-engine/facebook-ads-library-scraper` — comparable surface, slightly different field naming. The normalizer accepts both casings so swapping is a one-line change in `meta/scraper.py::META_ACTOR_ID`.

## X — `xtdata/twitter-x-scraper` (Phase 5)

Primary path. X's official Ad Transparency is EU-only and thin; we lean on this actor to detect promoted-tweet patterns, then enrich with the `business.x.com` CSV when in-scope.

## TikTok — Creative Center scraper (Phase 6)

Target source: `ads.tiktok.com/business/creativecenter/topads`. Pick the actor with the highest weekly success rate at PR time — they churn faster than Meta's.

## Google — Ads Transparency Center (Phase 6)

Target source: `adstransparency.google.com`. Coverage is much narrower than Meta's; mostly useful for cross-referencing advertiser-level intel.

## LinkedIn — Ad Library (Phase 6)

Target source: `linkedin.com/ad-library`. Only useful for B2B niches — keep but deprioritize.

## Cost discipline

Every run records a row in `apify_runs` before the dataset is parsed. The runner aborts above `APIFY_MAX_USD_PER_RUN` (default \$5). Review weekly with:

```sql
SELECT platform, sum(cost_usd) AS spend, count(*) AS runs, sum(item_count) AS items
FROM apify_runs
WHERE started_at > now() - interval '7 days' AND status = 'ok'
GROUP BY platform ORDER BY spend DESC;
```
