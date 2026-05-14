"""Seed the DB with realistic ads for demo / offline testing.

Doesn't hit any external API. Uses local BGE for embeddings and (if available)
local Ollama for AI analysis — so it runs with $0 and no tokens.

Run:  poetry run python scripts/seed_demo.py
"""
from __future__ import annotations

import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from adspy.analyzers.scoring import score_ad_row  # noqa: E402
from adspy.db.session import session_scope  # noqa: E402
from adspy.models.ad import Ad  # noqa: E402


def now_utc() -> datetime:
    return datetime.now(UTC)


# ─── seed data ────────────────────────────────────────────────────────────────

NICHES: list[dict] = [
    # niche: list of (advertiser_name, page_id, [(creative_type, headline, primary_text, days_ago, variants)])
    {
        "name": "cold_plunge",
        "advertisers": [
            ("Arctic Source", "page_cp_001", [
                ("video", "The cold plunge that changed my life",
                 "Most cold plunges leak by month 6. We engineered ours to last 25 years. Here's why elite athletes are switching to Arctic Source.", 95, 18),
                ("image", "Stop boiling money on broken plunges",
                 "Other tubs use plastic liners that warp. Ours is solid stainless. See the unboxing.", 47, 8),
            ]),
            ("Plunge Pro", "page_cp_002", [
                ("carousel", "From $4,500 to $897 — same temp, same gains",
                 "We cut out the retail markup. Same 39°F plunge. 5x the customers.", 134, 22),
                ("video", "Why I quit Plunge.com after 90 days",
                 "Honest review from a customer who tried both. Spoiler: the cheap one won.", 12, 4),
            ]),
        ],
    },
    {
        "name": "supplements",
        "advertisers": [
            ("MagnesiumDirect", "page_sup_001", [
                ("image", "Doctor: 70% of you are magnesium deficient",
                 "Dr. Reynolds explains why standard blood tests miss this. Take the 2-minute quiz to see your stack.", 78, 12),
                ("video", "Why I stopped taking 5 pills a day",
                 "Switched to one. Sleeping like a 20-year-old. Here's the formula.", 156, 31),
            ]),
            ("Liver Boost Co", "page_sup_002", [
                ("image", "Liver King is selling you snake oil",
                 "Real liver supplementation requires this one specific cofactor. Most brands skip it.", 34, 6),
            ]),
            ("DailyGreens", "page_sup_003", [
                ("video", "The $80 green powder scam",
                 "We tested 17 brands. Only 3 had what they claimed. Comparison inside.", 56, 14),
                ("text", "Stop buying Athletic Greens",
                 "Same ingredients, 1/3 the price. Subscription model. Cancel anytime.", 89, 9),
            ]),
        ],
    },
    {
        "name": "b2b_saas",
        "advertisers": [
            ("SaaSGrowth.io", "page_b2b_001", [
                ("video", "How we 3x'd our MRR in 60 days",
                 "Stop chasing leads. Start qualifying them. The framework we used to scale a $0 → $80k MRR SaaS.", 67, 16),
                ("image", "Founders making <$20k MRR — read this",
                 "Your problem isn't traffic. It's positioning. Free audit inside.", 23, 5),
            ]),
            ("PipeLine Pro", "page_b2b_002", [
                ("carousel", "We replaced HubSpot with this and saved $24K/yr",
                 "Same features, no marketing tax. Built by founders for founders.", 8, 2),
            ]),
        ],
    },
    {
        "name": "courses",
        "advertisers": [
            ("CodeAcademy Pro", "page_edu_001", [
                ("video", "I learned Python in 8 weeks and got hired at $145k",
                 "Bootcamps cost $15k. This is $97. Same outcome. Story inside.", 112, 27),
                ("image", "If you've been coding for 6 months but still feel lost",
                 "It's not you. It's the curriculum. We rebuilt it for actually-confused people.", 41, 9),
            ]),
            ("AI Mastery", "page_edu_002", [
                ("video", "ChatGPT prompts that 10x your output",
                 "Free PDF. No email needed. Just the 27 prompts our team uses daily.", 18, 6),
            ]),
        ],
    },
    {
        "name": "skincare",
        "advertisers": [
            ("Glow Lab", "page_skin_001", [
                ("image", "Before/After: 47-year-old in 90 days",
                 "She tried everything. Nothing worked until she switched to this exact regimen.", 73, 19),
                ("video", "Esthetician: stop using 12 products",
                 "You need 3. This is the truth most brands won't tell you.", 28, 8),
            ]),
            ("Pure Skin Co", "page_skin_002", [
                ("carousel", "Stop wasting money on retinol",
                 "Most retinol is denatured before it hits your skin. Here's how to tell.", 102, 15),
            ]),
        ],
    },
    {
        "name": "coaching",
        "advertisers": [
            ("Mindset Mastery", "page_coach_001", [
                ("video", "I made $1M before 30 — here's the system",
                 "Not motivation. Not affirmations. A specific decision framework anyone can copy.", 145, 24),
                ("image", "The 4am club is killing your dopamine",
                 "Productivity hustle culture is broken. Here's the science.", 7, 3),
            ]),
        ],
    },
    {
        "name": "pets",
        "advertisers": [
            ("HappyTails", "page_pet_001", [
                ("video", "Why your dog still has fleas in winter",
                 "Vet exposes the truth about year-round flea cycles. Most owners get this wrong.", 39, 7),
                ("image", "If your dog scratches at 3am, read this",
                 "It's not boredom. It's diet. We figured this out the expensive way.", 88, 11),
            ]),
        ],
    },
]

PLACEMENTS_POOLS = [
    ["facebook"],
    ["facebook", "instagram"],
    ["facebook", "instagram", "messenger"],
    ["facebook", "instagram", "messenger", "threads"],
]

COUNTRIES_POOLS = [
    ["US"],
    ["US", "CA"],
    ["US", "CA", "GB", "AU"],
]

REACH_BANDS = [None, None, "10000-50000", "50000-100000", "100000-500000", "500000-1000000", ">1000000"]

# Demo rip-off cluster: two advertisers run a near-identical creative.
SHARED_PHASH = "ff00ff00ff00ff00"  # all 16 hex chars


def build_records() -> list[dict]:
    rows: list[dict] = []
    seq = 0
    for niche in NICHES:
        for adv_name, page_id, ads in niche["advertisers"]:
            for ctype, headline, body, days_ago, variants in ads:
                seq += 1
                ad_id = f"100000000{seq:06d}"
                first_seen = now_utc() - timedelta(days=days_ago)
                last_seen = now_utc()
                placements = random.choice(PLACEMENTS_POOLS)
                countries = random.choice(COUNTRIES_POOLS)
                reach_band = random.choice(REACH_BANDS)

                row = {
                    "platform": "meta",
                    "ad_id": ad_id,
                    "advertiser_name": adv_name,
                    "advertiser_page_id": page_id,
                    "advertiser_url": f"https://www.facebook.com/{page_id}",
                    "first_seen": first_seen,
                    "last_seen": last_seen,
                    "days_active": (last_seen - first_seen).days,
                    "countries": countries,
                    "languages": ["en"],
                    "placements": placements,
                    "creative_type": ctype,
                    "headline": headline,
                    "primary_text": body,
                    "description": None,
                    "cta_text": "Learn More" if ctype != "video" else "Shop Now",
                    "cta_url": None,
                    "landing_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
                    "variant_count": variants,
                    "reach_band": reach_band,
                    "raw_json": {"seed": True, "niche": niche["name"]},
                    "updated_at": now_utc(),
                }
                row["winner_score"] = score_ad_row(row)
                rows.append(row)
    return rows


def main() -> int:
    random.seed(42)
    rows = build_records()
    for r in rows:
        r["media_phash"] = None  # ensure column present in every row

    # Seed a cross-advertiser rip-off pair via shared pHash.
    rows[0]["media_phash"] = [SHARED_PHASH]
    rows[2]["media_phash"] = [SHARED_PHASH]  # different advertiser, same niche
    rows[7]["media_phash"] = ["aabbccddeeff0011"]  # singleton (no rip-off)

    with session_scope() as s:
        stmt = insert(Ad).values(rows)
        update_cols = {
            c.name: getattr(stmt.excluded, c.name)
            for c in Ad.__table__.columns
            if c.name not in ("platform", "ad_id", "created_at")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "ad_id"], set_=update_cols
        )
        s.execute(stmt)

    print(f"seeded {len(rows)} ads across {len(NICHES)} niches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
