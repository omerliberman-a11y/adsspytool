import Link from "next/link";
import type { AdListResp } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const HOOKS = [
  "curiosity",
  "authority",
  "fear",
  "problem_agitation",
  "transformation",
  "before_after",
  "social_proof",
  "contrarian",
  "pattern_interrupt",
  "listicle",
  "qa",
];

async function topAdsByHook(hook: string): Promise<AdListResp> {
  const qs = new URLSearchParams({
    hook_type: hook,
    limit: "4",
    min_score: "50",
  });
  const r = await fetch(`${API}/ads?${qs}`, { cache: "no-store" });
  if (!r.ok) return { count: 0, items: [] };
  return r.json();
}

export default async function PlaybooksPage() {
  const blocks = await Promise.all(HOOKS.map((h) => topAdsByHook(h)));

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-2">Playbooks</h1>
      <p className="text-sm text-muted mb-6">
        Top-scoring ads grouped by hook archetype. Browse tactics, not just ads.
      </p>

      <div className="space-y-8">
        {HOOKS.map((hook, i) => {
          const ads = blocks[i].items;
          if (ads.length === 0) return null;
          return (
            <section key={hook}>
              <h2 className="text-lg font-semibold mb-3 capitalize">
                {hook.replace("_", " ")}
                <span className="text-muted text-xs ml-2 font-normal">
                  {blocks[i].count} winners
                </span>
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {ads.map((ad) => (
                  <Link
                    key={`${ad.platform}/${ad.ad_id}`}
                    href={`/ads/${ad.platform}/${ad.ad_id}`}
                    className="bg-panel border border-border rounded overflow-hidden hover:border-accent"
                  >
                    {ad.media_urls?.[0] ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={ad.media_urls[0]}
                        alt=""
                        className="w-full aspect-square object-cover"
                      />
                    ) : (
                      <div className="w-full aspect-square grid place-items-center text-muted text-xs">
                        no media
                      </div>
                    )}
                    <div className="p-2 text-xs">
                      <div className="text-muted truncate">{ad.advertiser_name ?? "?"}</div>
                      <div className="line-clamp-2 min-h-[2em] mt-0.5">
                        {ad.ai_hook ?? ad.headline ?? ad.primary_text ?? ""}
                      </div>
                      <div className="text-muted mt-1">score {ad.winner_score ?? "—"}</div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
