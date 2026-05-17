"use client";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { CLIENT_API_BASE, fetcher } from "@/lib/api";

const API = CLIENT_API_BASE;

type SavedSearch = {
  id: number;
  name: string;
  platform: string;
  task_kind: string;
  params: Record<string, unknown>;
  enabled: boolean;
  interval_minutes: number;
  last_run_at: string | null;
  last_task_id: number | null;
  last_error: string | null;
  next_run_at: string | null;
};

type Platform = "meta" | "tiktok";

export default function SchedulePage() {
  const { data, error, isLoading } = useSWR<{ count: number; items: SavedSearch[] }>(
    `${API}/saved-searches`,
    fetcher,
    { refreshInterval: 5000 },
  );

  // form state
  const [platform, setPlatform] = useState<Platform>("tiktok");
  const [name, setName] = useState("");
  const [country, setCountry] = useState("US");
  const [period, setPeriod] = useState<7 | 30 | 120>(30);
  const [keyword, setKeyword] = useState("");
  const [pageId, setPageId] = useState("");
  const [limit, setLimit] = useState(50);
  const [intervalHr, setIntervalHr] = useState(24);
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setMsg(null);
    try {
      const body: Record<string, unknown> = {
        name: name || `${platform} ${country} ${period}d`,
        platform,
        task_kind: `scrape_${platform}`,
        interval_minutes: intervalHr * 60,
        params:
          platform === "tiktok"
            ? { country: country.toUpperCase(), period, limit }
            : {
                keyword: keyword || null,
                advertiser_page: pageId || null,
                countries: [country.toUpperCase()],
                active_only: true,
                limit,
              },
      };
      const r = await fetch(`${API}/saved-searches`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!r.ok) setMsg(`error: ${JSON.stringify(j)}`);
      else {
        setMsg(`saved as #${j.id}. Will fire on next scheduler tick (≤60s).`);
        setName("");
        mutate(`${API}/saved-searches`);
      }
    } catch (err) {
      setMsg(`error: ${String(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleEnabled(s: SavedSearch) {
    await fetch(`${API}/saved-searches/${s.id}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ enabled: !s.enabled }),
    });
    mutate(`${API}/saved-searches`);
  }
  async function runNow(s: SavedSearch) {
    await fetch(`${API}/saved-searches/${s.id}/run-now`, { method: "POST" });
    mutate(`${API}/saved-searches`);
  }
  async function deleteOne(s: SavedSearch) {
    if (!confirm(`Delete saved search "${s.name}"?`)) return;
    await fetch(`${API}/saved-searches/${s.id}`, { method: "DELETE" });
    mutate(`${API}/saved-searches`);
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Scheduled scrapes</h1>
        <p className="text-sm text-muted mt-1">
          Saved searches that re-run every N hours. The in-process scheduler ticks every minute and
          enqueues any saved search whose next run has passed.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
        <div>
          <h2 className="text-lg font-semibold mb-3">Active schedules</h2>
          {error && <div className="text-bad">Backend unreachable.</div>}
          {isLoading && <div className="text-muted">Loading…</div>}
          {data && data.items.length === 0 && (
            <div className="border border-dashed border-border rounded-lg p-10 text-center text-muted">
              No schedules yet. Add one on the right →
            </div>
          )}
          {data && data.items.length > 0 && (
            <div className="bg-panel border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-bg text-muted text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-3 py-2">Name</th>
                    <th className="text-left px-3 py-2">Kind</th>
                    <th className="text-left px-3 py-2">Every</th>
                    <th className="text-left px-3 py-2">Next run</th>
                    <th className="text-left px-3 py-2">Last</th>
                    <th className="text-right px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((s) => (
                    <tr key={s.id} className="border-t border-border">
                      <td className="px-3 py-2">
                        <div className="font-medium">{s.name}</div>
                        <div className="text-[10px] text-muted font-mono mt-0.5">
                          {JSON.stringify(s.params).slice(0, 60)}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className="px-1.5 py-0.5 rounded bg-bg text-muted font-mono text-[10px] uppercase">
                          {s.platform}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {s.interval_minutes >= 60
                          ? `${Math.round(s.interval_minutes / 60)}h`
                          : `${s.interval_minutes}m`}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted">
                        {s.next_run_at ? rel(s.next_run_at) : "—"}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {s.last_task_id ? (
                          <span className="text-good">#{s.last_task_id}</span>
                        ) : (
                          <span className="text-muted">never</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">
                        <button
                          onClick={() => toggleEnabled(s)}
                          className={`text-xs px-2 py-1 rounded mr-1 ${
                            s.enabled
                              ? "bg-good/20 text-good"
                              : "bg-muted/20 text-muted"
                          }`}
                        >
                          {s.enabled ? "on" : "off"}
                        </button>
                        <button
                          onClick={() => runNow(s)}
                          className="text-xs px-2 py-1 rounded bg-accent text-white mr-1"
                        >
                          Run now
                        </button>
                        <button
                          onClick={() => deleteOne(s)}
                          className="text-xs px-2 py-1 rounded border border-border text-muted hover:text-bad"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-3">+ New schedule</h2>
          <form
            onSubmit={submit}
            className="space-y-3 bg-panel border border-border rounded-lg p-5"
          >
            <div className="flex gap-2 mb-3">
              {(["tiktok", "meta"] as Platform[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPlatform(p)}
                  className={`flex-1 px-3 py-2 rounded text-sm font-medium ${
                    platform === p
                      ? "bg-accent text-white"
                      : "bg-bg border border-border text-muted"
                  }`}
                >
                  {p.toUpperCase()}
                </button>
              ))}
            </div>
            <Row label="Name (optional)">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Cold plunge US daily"
                className="w-full bg-bg border border-border rounded px-3 py-2"
              />
            </Row>
            {platform === "meta" && (
              <>
                <Row label="Keyword">
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    className="w-full bg-bg border border-border rounded px-3 py-2"
                  />
                </Row>
                <Row label="OR Page ID">
                  <input
                    type="text"
                    value={pageId}
                    onChange={(e) => setPageId(e.target.value)}
                    className="w-full bg-bg border border-border rounded px-3 py-2"
                  />
                </Row>
              </>
            )}
            {platform === "tiktok" && (
              <Row label="Period">
                <select
                  value={period}
                  onChange={(e) => setPeriod(parseInt(e.target.value, 10) as 7 | 30 | 120)}
                  className="w-full bg-bg border border-border rounded px-3 py-2"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={120}>Last 120 days</option>
                </select>
              </Row>
            )}
            <Row label="Country">
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                maxLength={5}
                className="w-32 bg-bg border border-border rounded px-3 py-2 uppercase"
              />
            </Row>
            <Row label="Limit per run">
              <input
                type="number"
                value={limit}
                min={1}
                max={500}
                onChange={(e) => setLimit(parseInt(e.target.value || "0", 10))}
                className="w-32 bg-bg border border-border rounded px-3 py-2"
              />
            </Row>
            <Row label="Re-run every (hours)">
              <input
                type="number"
                value={intervalHr}
                min={1}
                max={168}
                onChange={(e) => setIntervalHr(parseInt(e.target.value || "0", 10))}
                className="w-32 bg-bg border border-border rounded px-3 py-2"
              />
            </Row>
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 rounded-md bg-accent text-white font-medium disabled:opacity-50"
            >
              {submitting ? "Saving…" : "+ Add schedule"}
            </button>
            {msg && <div className="text-sm text-muted pt-1">{msg}</div>}
          </form>
        </div>
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs uppercase tracking-wider text-muted mb-1">{label}</div>
      {children}
    </label>
  );
}

function rel(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms < 0) {
    const abs = Math.abs(ms);
    if (abs < 60_000) return "now";
    if (abs < 3600_000) return `${Math.floor(abs / 60_000)}m overdue`;
    return `${Math.floor(abs / 3600_000)}h overdue`;
  }
  if (ms < 60_000) return `in <1m`;
  if (ms < 3600_000) return `in ${Math.floor(ms / 60_000)}m`;
  if (ms < 86400_000) return `in ${Math.floor(ms / 3600_000)}h`;
  return `in ${Math.floor(ms / 86400_000)}d`;
}
