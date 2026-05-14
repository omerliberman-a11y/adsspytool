import type { Stats } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function loadStats(): Promise<Stats | null> {
  const r = await fetch(`${API}/stats`, { cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

export default async function StatsPage() {
  const s = await loadStats();
  if (!s) {
    return <div className="text-muted">Backend unreachable — start the API.</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Stats</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <Stat label="Total ads" value={s.ads.total} />
        <Stat label="Scraped today" value={s.scrape_runs_today} />
        <Stat label="AI calls today" value={s.ai_today.total} />
        <Stat label="Tasks queued" value={s.tasks_by_status?.queued ?? 0} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Panel title="By platform" rows={s.ads.per_platform} />
        <Panel title="By creative type" rows={s.ads.per_creative_type} />
        <Panel title="By hook type" rows={s.ads.per_hook_type} />
        <Panel title="Winner-score buckets" rows={s.ads.winner_score_buckets} />
        <Panel title="AI calls by provider (today)" rows={s.ai_today.per_provider} />
        <Panel title="Tasks by status" rows={s.tasks_by_status} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className="text-2xl font-mono mt-1">{value}</div>
    </div>
  );
}

function Panel({ title, rows }: { title: string; rows: Record<string, number> }) {
  const entries = Object.entries(rows || {}).filter(([k]) => k && k !== "null");
  if (entries.length === 0)
    return (
      <div className="bg-panel border border-border rounded-lg p-4">
        <div className="text-xs uppercase tracking-wider text-muted mb-3">{title}</div>
        <div className="text-muted text-sm">—</div>
      </div>
    );
  const max = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="bg-panel border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-muted mb-3">{title}</div>
      <div className="space-y-2">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-3 text-sm">
            <span className="w-44 truncate text-muted">{k}</span>
            <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
              <div
                className="h-full bg-accent"
                style={{ width: `${(v / max) * 100}%` }}
              />
            </div>
            <span className="w-10 text-right font-mono">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
