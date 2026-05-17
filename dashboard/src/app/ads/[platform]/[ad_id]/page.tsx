import Link from "next/link";
import type { Ad } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function loadAd(platform: string, ad_id: string): Promise<Ad | null> {
  const r = await fetch(`${API}/ads/${platform}/${ad_id}`, { cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

async function loadSimilar(platform: string, ad_id: string, by: "copy" | "image") {
  const r = await fetch(
    `${API}/similar/${platform}/${ad_id}?by=${by}&limit=8`,
    { cache: "no-store" },
  );
  if (!r.ok) return { items: [] as Ad[] };
  return r.json() as Promise<{ items: Ad[] }>;
}

type Props = { params: Promise<{ platform: string; ad_id: string }> };

export default async function AdPage({ params }: Props) {
  const { platform, ad_id } = await params;
  const ad = await loadAd(platform, ad_id);
  if (!ad) return <div className="text-muted">Ad not found.</div>;

  const [bycopy, byimage] = await Promise.all([
    loadSimilar(platform, ad_id, "copy"),
    loadSimilar(platform, ad_id, "image"),
  ]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
      <div>
        <div className="mb-4">
          <Link href="/" className="text-sm text-muted hover:text-ink">
            ← All winners
          </Link>
        </div>

        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-panel border border-border">
            {ad.platform}
          </span>
          <h1 className="text-xl font-semibold flex-1">{ad.advertiser_name ?? "?"}</h1>
          <span
            className={`text-lg font-mono px-3 py-1 rounded ${
              (ad.winner_score ?? 0) >= 80
                ? "bg-good/20 text-good"
                : (ad.winner_score ?? 0) >= 60
                  ? "bg-warn/20 text-warn"
                  : "bg-panel"
            }`}
          >
            {ad.winner_score ?? "—"}
          </span>
        </div>

        <div className="bg-panel border border-border rounded-lg overflow-hidden mb-6">
          {ad.media_urls && ad.media_urls.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
              {ad.media_urls.slice(0, 4).map((url, i) =>
                ad.creative_type === "video" && i === 0 ? (
                  <video
                    key={url}
                    src={url}
                    controls
                    className="w-full aspect-square object-cover bg-black"
                  />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={url}
                    src={url}
                    alt=""
                    className="w-full aspect-square object-cover bg-black"
                  />
                ),
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-muted">
              media not yet resolved — snapshot_replay task pending
            </div>
          )}
        </div>

        {ad.ai_hook && (
          <Section title="AI hook">
            <p className="text-lg">{ad.ai_hook}</p>
          </Section>
        )}

        {ad.ai_summary && (
          <Section title="Why this works">
            <p>{ad.ai_summary}</p>
          </Section>
        )}

        {(ad.headline || ad.primary_text) && (
          <Section title="Original copy">
            {ad.headline && <div className="font-semibold mb-1">{ad.headline}</div>}
            {ad.primary_text && (
              <div className="whitespace-pre-wrap text-muted">{ad.primary_text}</div>
            )}
            {ad.description && (
              <div className="mt-2 text-sm text-muted">{ad.description}</div>
            )}
          </Section>
        )}

        {ad.ai_rewritten_copy && ad.ai_rewritten_copy.length > 0 && (
          <Section title="Rewritten variants">
            <div className="space-y-3">
              {ad.ai_rewritten_copy.map((v, i) => (
                <div
                  key={i}
                  className="bg-panel border border-border rounded p-3 text-sm whitespace-pre-wrap"
                >
                  {v}
                </div>
              ))}
            </div>
          </Section>
        )}

        <DestinationPanel ad={ad} />

        <SimilarBlock title="More like this — by copy" items={bycopy.items} />
        <SimilarBlock title="More like this — by image" items={byimage.items} />
      </div>

      <aside className="bg-panel border border-border rounded-lg p-4 h-fit sticky top-20 space-y-3 text-sm">
        {ad.source_url && (
          <a
            href={ad.source_url}
            target="_blank"
            rel="noreferrer"
            className="block text-center px-3 py-2 rounded bg-accent text-white text-sm font-medium hover:opacity-90"
          >
            ▶ View ad on {platformLabel(ad.platform)}
          </a>
        )}
        {ad.final_url && (
          <a
            href={ad.final_url}
            target="_blank"
            rel="noreferrer"
            className="block text-center px-3 py-2 rounded border border-border text-sm font-medium hover:border-accent"
          >
            ↗ Open product page
          </a>
        )}

        <hr className="border-border" />
        <Row label="Hook type" v={ad.hook_type} />
        <Row label="Awareness stage" v={ad.awareness_stage} />
        <Row label="Copy framework" v={ad.copy_framework} />
        <Row label="Angle" v={ad.ai_angle} />
        <Row label="Offer" v={ad.ai_offer} />
        <hr className="border-border" />
        <Row label="Days active" v={ad.days_active} />
        <Row label="Variants" v={ad.variant_count} />
        <Row label="Creative" v={ad.creative_type} />
        <Row label="Placements" v={ad.placements?.join(", ")} />
        <Row label="Countries" v={ad.countries?.join(", ")} />
        <Row label="Languages" v={ad.languages?.join(", ")} />
        <Row label="Reach band" v={ad.reach_band} />
        <Row label="First seen" v={fmt(ad.first_seen)} />
        <Row label="Last seen" v={fmt(ad.last_seen)} />
        {ad.advertiser_url && (
          <a
            href={ad.advertiser_url}
            target="_blank"
            rel="noreferrer"
            className="block text-accent text-sm mt-2"
          >
            View advertiser page →
          </a>
        )}
      </aside>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <div className="text-xs uppercase tracking-wider text-muted mb-2">{title}</div>
      {children}
    </section>
  );
}

function platformLabel(p: string): string {
  return {
    meta: "Meta Ad Library",
    tiktok: "TikTok",
    x: "X",
    google: "Google",
    linkedin: "LinkedIn",
  }[p] ?? p;
}

function DestinationPanel({ ad }: { ad: Ad }) {
  if (!ad.link_chain || ad.link_chain.length === 0) {
    if (!ad.cta_url && !ad.landing_url) {
      return null;
    }
    return (
      <Section title="Destination">
        <div className="bg-panel border border-border rounded p-3 text-sm text-muted">
          Not resolved yet. Click <code className="text-accent">/admin/ads/{ad.platform}/{ad.ad_id}/resolve-link</code> to enqueue.
        </div>
      </Section>
    );
  }
  return (
    <Section title="Destination">
      <div className="bg-panel border border-border rounded-lg p-4">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wider text-muted">final →</span>
            <span className="font-mono">{ad.final_domain}</span>
            {ad.affiliate_network && (
              <span className="px-2 py-0.5 rounded bg-warn/20 text-warn text-xs font-mono uppercase">
                {ad.affiliate_network} affiliate
              </span>
            )}
          </div>
          {ad.final_url && (
            <a
              href={ad.final_url}
              target="_blank"
              rel="noreferrer"
              className="text-accent text-sm"
            >
              Open ↗
            </a>
          )}
        </div>

        <div className="text-xs uppercase tracking-wider text-muted mb-2">
          {ad.link_chain.length} hop{ad.link_chain.length === 1 ? "" : "s"}
        </div>
        <ol className="space-y-1.5 text-xs font-mono">
          {ad.link_chain.map((h, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="text-muted w-6 text-right">{h.index}</span>
              <StatusBadge status={h.status} kind={h.kind} />
              <span className="truncate text-ink">{h.host}</span>
              {h.affiliate && (
                <span className="px-1.5 py-0 rounded bg-warn/20 text-warn text-[10px] uppercase">
                  {h.affiliate}
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>
    </Section>
  );
}

function StatusBadge({ status, kind }: { status: number | null; kind: string }) {
  if (kind === "error") {
    return <span className="px-1.5 rounded bg-bad/20 text-bad text-[10px]">ERR</span>;
  }
  if (kind === "meta_refresh") {
    return <span className="px-1.5 rounded bg-accent/20 text-accent text-[10px]">META</span>;
  }
  if (kind === "js") {
    return <span className="px-1.5 rounded bg-accent/20 text-accent text-[10px]">JS</span>;
  }
  if (status === null) {
    return <span className="px-1.5 rounded bg-muted/20 text-muted text-[10px]">—</span>;
  }
  const color =
    status >= 200 && status < 300
      ? "bg-good/20 text-good"
      : status >= 300 && status < 400
        ? "bg-warn/20 text-warn"
        : "bg-bad/20 text-bad";
  return <span className={`px-1.5 rounded text-[10px] ${color}`}>{status}</span>;
}

function Row({ label, v }: { label: string; v: unknown }) {
  const display =
    v === null || v === undefined || v === "" ? <span className="text-muted">—</span> : String(v);
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className="text-right">{display}</span>
    </div>
  );
}

function fmt(s: string | null): string | null {
  if (!s) return null;
  try {
    return new Date(s).toISOString().slice(0, 10);
  } catch {
    return s;
  }
}

function SimilarBlock({ title, items }: { title: string; items: Ad[] }) {
  if (items.length === 0) return null;
  return (
    <Section title={title}>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {items.map((a) => (
          <Link
            key={`${a.platform}/${a.ad_id}`}
            href={`/ads/${a.platform}/${a.ad_id}`}
            className="bg-panel border border-border rounded overflow-hidden hover:border-accent"
          >
            {a.media_urls?.[0] ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={a.media_urls[0]}
                alt=""
                className="w-full aspect-square object-cover"
              />
            ) : (
              <div className="w-full aspect-square grid place-items-center text-muted text-xs">
                no media
              </div>
            )}
            <div className="px-2 py-1.5 text-xs">
              <div className="truncate text-muted">{a.advertiser_name ?? "?"}</div>
              <div className="truncate">{a.ai_hook ?? a.headline ?? a.primary_text ?? ""}</div>
            </div>
          </Link>
        ))}
      </div>
    </Section>
  );
}
