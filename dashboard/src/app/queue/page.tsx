"use client";
import useSWR from "swr";
import { CLIENT_API_BASE, fetcher } from "@/lib/api";
import type { Task } from "@/lib/api";

export default function QueuePage() {
  const { data, error, isLoading } = useSWR<{ count: number; items: Task[] }>(
    `${CLIENT_API_BASE}/tasks?limit=50`,
    fetcher,
    { refreshInterval: 3000 },
  );

  if (error) return <div className="text-bad">Backend unreachable.</div>;
  if (isLoading || !data) return <div className="text-muted">Loading…</div>;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-2">Task queue</h1>
      <p className="text-sm text-muted mb-6">
        Live view of the Postgres-backed queue. Refreshes every 3s.
      </p>

      <div className="bg-panel border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg text-muted text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-3 py-2">ID</th>
              <th className="text-left px-3 py-2">Kind</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Attempts</th>
              <th className="text-left px-3 py-2">Created</th>
              <th className="text-left px-3 py-2">Error</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="px-3 py-2 font-mono text-muted">{t.id}</td>
                <td className="px-3 py-2 font-mono">{t.kind}</td>
                <td className="px-3 py-2">
                  <StatusPill status={t.status} />
                </td>
                <td className="px-3 py-2 font-mono">
                  {t.attempts}/{t.max_attempts}
                </td>
                <td className="px-3 py-2 text-muted">{ago(t.created_at)}</td>
                <td className="px-3 py-2 text-bad truncate max-w-[400px]">{t.error ?? ""}</td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-muted py-8">
                  No tasks yet — enqueue something from{" "}
                  <a className="text-accent" href="/scrape">
                    /scrape
                  </a>
                  .
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const color =
    {
      queued: "bg-muted/20 text-muted",
      running: "bg-warn/20 text-warn",
      done: "bg-good/20 text-good",
      failed: "bg-bad/20 text-bad",
      retrying: "bg-accent/20 text-accent",
    }[status] ?? "bg-panel";
  return <span className={`px-2 py-0.5 rounded text-xs font-mono ${color}`}>{status}</span>;
}

function ago(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86400_000) return `${Math.floor(ms / 3600_000)}h ago`;
  return `${Math.floor(ms / 86400_000)}d ago`;
}
