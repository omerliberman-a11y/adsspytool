import Link from "next/link";
import { AdCard } from "@/components/AdCard";
import type { Ad } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Competitor = {
  id: number;
  domain: string;
  name: string | null;
  fb_page_url: string | null;
  fb_page_id: string | null;
  instagram_handle: string | null;
  tiktok_handle: string | null;
  twitter_handle: string | null;
  youtube_channel: string | null;
  linkedin_company: string | null;
  tech_stack: string[] | null;
  pixels: string[] | null;
  ad_count: number | null;
  last_enriched_at: string | null;
  last_scanned_at: string | null;
  last_scan_error: string | null;
};

async function loadCompetitor(id: string): Promise<Competitor | null> {
  const r = await fetch(`${API}/competitors/${id}`, { cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

async function loadAds(id: string): Promise<Ad[]> {
  // We need a generic /ads filter — using advertiser_page_id (added in latest API).
  // First, get the competitor to know its fb_page_id; then filter.
  const c = await loadCompetitor(id);
  if (!c?.fb_page_id) return [];
  const r = await fetch(
    `${API}/ads?advertiser_page_id=${encodeURIComponent(c.fb_page_id)}&limit=200`,
    { cache: "no-store" }
  );
  if (!r.ok) return [];
  const data = (await r.json()) as { items: Ad[] };
  return data.items;
}

type Props = { params: Promise<{ id: string }> };

export default async function CompetitorDetail({ params }: Props) {
  const { id } = await params;
  const [c, ads] = await Promise.all([loadCompetitor(id), loadAds(id)]);
  if (!c) {
    return <div className="text-muted">Competitor not found.</div>;
  }

  return (
    <div>
      <div className="mb-4">
        <Link href="/competitors" className="text-sm text-muted hover:text-ink">
          ← All competitors
        </Link>
      </div>

      <div className="flex items-baseline gap-3 mb-1">
        <h1 className="text-2xl font-semibold">{c.domain}</h1>
        {c.name && <span className="text-muted">{c.name}</span>}
      </div>
      <div className="text-sm text-muted mb-6">
        {c.ad_count ?? 0} ads tracked
        {c.last_scanned_at && ` · last scan ${ago(c.last_scanned_at)}`}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        <Panel title="Facebook">
          {c.fb_page_id ? (
            <>
              <div className="font-mono text-xs">{c.fb_page_id}</div>
              {c.fb_page_url && (
                <a
                  href={c.fb_page_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent text-sm"
                >
                  Open page →
                </a>
              )}
            </>
          ) : (
            <span className="text-muted text-sm">Not resolved yet</span>
          )}
        </Panel>

        <Panel title="Socials">
          <SocialList c={c} />
        </Panel>

        <Panel title="Tech stack">
          {c.tech_stack && c.tech_stack.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {c.tech_stack.map((t) => (
                <span
                  key={t}
                  className="px-2 py-0.5 rounded bg-bg text-ink text-xs font-mono"
                >
                  {t}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-muted text-sm">None detected</span>
          )}
          {c.pixels && c.pixels.length > 0 && (
            <div className="mt-3 text-xs text-muted">
              Pixels:
              <div className="flex flex-wrap gap-1 mt-1">
                {c.pixels.map((p) => (
                  <span key={p} className="font-mono">{p}</span>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>

      <h2 className="text-lg font-semibold mb-3">Ads</h2>
      {ads.length === 0 ? (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-muted">
          No ads yet. Click <b>Scan now</b> on the list page once Facebook page is resolved.
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {ads.map((a) => (
            <AdCard key={`${a.platform}/${a.ad_id}`} ad={a} />
          ))}
        </div>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-muted mb-2">{title}</div>
      {children}
    </div>
  );
}

function SocialList({ c }: { c: Competitor }) {
  const rows: { label: string; value: string; href?: string }[] = [];
  if (c.instagram_handle)
    rows.push({
      label: "instagram",
      value: `@${c.instagram_handle}`,
      href: `https://instagram.com/${c.instagram_handle}`,
    });
  if (c.tiktok_handle)
    rows.push({
      label: "tiktok",
      value: `@${c.tiktok_handle}`,
      href: `https://tiktok.com/@${c.tiktok_handle}`,
    });
  if (c.twitter_handle)
    rows.push({
      label: "x/twitter",
      value: `@${c.twitter_handle}`,
      href: `https://x.com/${c.twitter_handle}`,
    });
  if (c.youtube_channel)
    rows.push({
      label: "youtube",
      value: c.youtube_channel,
      href: c.youtube_channel.startsWith("@")
        ? `https://youtube.com/${c.youtube_channel}`
        : `https://youtube.com/channel/${c.youtube_channel}`,
    });
  if (c.linkedin_company)
    rows.push({
      label: "linkedin",
      value: c.linkedin_company,
      href: `https://linkedin.com/company/${c.linkedin_company}`,
    });
  if (rows.length === 0)
    return <span className="text-muted text-sm">None detected</span>;
  return (
    <div className="space-y-1 text-sm">
      {rows.map((r) => (
        <div key={r.label} className="flex justify-between gap-2">
          <span className="text-muted">{r.label}</span>
          {r.href ? (
            <a
              href={r.href}
              target="_blank"
              rel="noreferrer"
              className="text-accent truncate"
            >
              {r.value}
            </a>
          ) : (
            <span className="truncate">{r.value}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function ago(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h ago`;
  return `${Math.floor(ms / 86400_000)}d ago`;
}
