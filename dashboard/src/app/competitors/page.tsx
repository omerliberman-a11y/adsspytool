"use client";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import Link from "next/link";
import { fetcher } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Competitor = {
  id: number;
  domain: string;
  name: string | null;
  tags: string[] | null;
  fb_page_url: string | null;
  fb_page_id: string | null;
  instagram_handle: string | null;
  tiktok_handle: string | null;
  twitter_handle: string | null;
  tech_stack: string[] | null;
  pixels: string[] | null;
  ad_count: number | null;
  last_enriched_at: string | null;
  last_scanned_at: string | null;
  last_scan_error: string | null;
};

export default function CompetitorsPage() {
  const { data, error, isLoading } = useSWR<{ count: number; items: Competitor[] }>(
    `${API}/competitors`,
    fetcher,
    { refreshInterval: 5000 }
  );

  const [domain, setDomain] = useState("");
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);

  async function addCompetitor(e: React.FormEvent) {
    e.preventDefault();
    if (!domain.trim()) return;
    setAdding(true);
    try {
      const r = await fetch(`${API}/competitors`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          domain: domain.trim(),
          name: name.trim() || null,
          tags: [],
        }),
      });
      if (r.ok) {
        setDomain("");
        setName("");
        mutate(`${API}/competitors`);
      }
    } finally {
      setAdding(false);
    }
  }

  async function triggerScan(id: number) {
    await fetch(`${API}/competitors/${id}/scan`, { method: "POST" });
    mutate(`${API}/competitors`);
  }
  async function triggerEnrich(id: number) {
    await fetch(`${API}/competitors/${id}/enrich`, { method: "POST" });
    mutate(`${API}/competitors`);
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-2xl font-semibold">Competitors</h1>
        <span className="text-sm text-muted">{data?.count ?? 0} tracked</span>
      </div>

      <form
        onSubmit={addCompetitor}
        className="bg-panel border border-border rounded-lg p-4 mb-6 flex gap-2 items-end"
      >
        <label className="flex-1 flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider text-muted">Domain</span>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="armra.com"
            className="bg-bg border border-border rounded px-3 py-2"
          />
        </label>
        <label className="flex-1 flex flex-col gap-1">
          <span className="text-xs uppercase tracking-wider text-muted">Name (optional)</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Armra"
            className="bg-bg border border-border rounded px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={adding || !domain.trim()}
          className="px-4 py-2 rounded bg-accent text-white font-medium disabled:opacity-50"
        >
          {adding ? "Adding…" : "+ Track"}
        </button>
      </form>

      {error && <div className="text-bad">Backend unreachable.</div>}
      {isLoading && <div className="text-muted">Loading…</div>}

      {data && data.items.length === 0 && (
        <div className="border border-dashed border-border rounded-lg p-12 text-center text-muted">
          No competitors yet. Add a domain above — enrichment will auto-discover their FB page,
          social handles, and tech stack within seconds.
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="bg-panel border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-bg text-muted text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-3 py-2">Domain</th>
                <th className="text-left px-3 py-2">FB Page</th>
                <th className="text-left px-3 py-2">Socials</th>
                <th className="text-left px-3 py-2">Tech</th>
                <th className="text-right px-3 py-2">Ads</th>
                <th className="text-left px-3 py-2">Status</th>
                <th className="text-right px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id} className="border-t border-border align-top">
                  <td className="px-3 py-3">
                    <Link
                      href={`/competitors/${c.id}`}
                      className="text-ink hover:text-accent font-medium"
                    >
                      {c.domain}
                    </Link>
                    {c.name && <div className="text-xs text-muted">{c.name}</div>}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs">
                    {c.fb_page_id ? (
                      <a
                        href={c.fb_page_url ?? "#"}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent"
                      >
                        {c.fb_page_id}
                      </a>
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-xs">
                    <SocialChips c={c} />
                  </td>
                  <td className="px-3 py-3 text-xs">
                    <TechChips items={c.tech_stack} />
                  </td>
                  <td className="px-3 py-3 text-right font-mono">{c.ad_count ?? 0}</td>
                  <td className="px-3 py-3 text-xs">
                    <StatusCell c={c} />
                  </td>
                  <td className="px-3 py-3 text-right whitespace-nowrap">
                    {!c.fb_page_id ? (
                      <button
                        onClick={() => triggerEnrich(c.id)}
                        className="text-xs px-2 py-1 rounded border border-border hover:border-accent"
                      >
                        Enrich
                      </button>
                    ) : (
                      <button
                        onClick={() => triggerScan(c.id)}
                        className="text-xs px-2 py-1 rounded bg-accent text-white"
                      >
                        Scan now
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SocialChips({ c }: { c: Competitor }) {
  const chips: { label: string; href?: string }[] = [];
  if (c.instagram_handle) chips.push({ label: `ig:${c.instagram_handle}`, href: `https://instagram.com/${c.instagram_handle}` });
  if (c.tiktok_handle) chips.push({ label: `tk:${c.tiktok_handle}` });
  if (c.twitter_handle) chips.push({ label: `x:${c.twitter_handle}` });
  if (chips.length === 0) return <span className="text-muted">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {chips.map((ch) => (
        <span
          key={ch.label}
          className="px-1.5 py-0.5 rounded bg-bg text-muted font-mono text-[10px]"
        >
          {ch.label}
        </span>
      ))}
    </div>
  );
}

function TechChips({ items }: { items: string[] | null }) {
  if (!items || items.length === 0) return <span className="text-muted">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.slice(0, 5).map((t) => (
        <span
          key={t}
          className="px-1.5 py-0.5 rounded bg-bg text-ink font-mono text-[10px]"
        >
          {t}
        </span>
      ))}
      {items.length > 5 && <span className="text-muted">+{items.length - 5}</span>}
    </div>
  );
}

function StatusCell({ c }: { c: Competitor }) {
  if (c.last_scan_error) {
    return <span className="text-bad" title={c.last_scan_error}>error</span>;
  }
  if (c.last_scanned_at) {
    return <span className="text-good">scanned {ago(c.last_scanned_at)}</span>;
  }
  if (c.last_enriched_at) {
    return <span className="text-warn">enriched, awaiting scan</span>;
  }
  return <span className="text-muted">pending enrich</span>;
}

function ago(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h ago`;
  return `${Math.floor(ms / 86400_000)}d ago`;
}
