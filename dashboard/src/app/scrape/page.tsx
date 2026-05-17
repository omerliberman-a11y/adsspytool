"use client";
import { useState } from "react";
import { CLIENT_API_BASE } from "@/lib/api";

const API = CLIENT_API_BASE;

type Platform = "meta" | "tiktok";

export default function ScrapePage() {
  const [platform, setPlatform] = useState<Platform>("meta");

  // meta-specific
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState("");
  const [active, setActive] = useState(true);
  const [metaSurfaces, setMetaSurfaces] = useState<string[]>([]);  // [] = all surfaces

  // shared
  const [country, setCountry] = useState("US");
  const [limit, setLimit] = useState(50);

  // tiktok-specific
  const [period, setPeriod] = useState<7 | 30 | 120>(30);

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);
    setSubmitting(true);
    try {
      let url = "";
      let body: Record<string, unknown> = {};
      if (platform === "meta") {
        url = `${API}/scrape/meta`;
        body = {
          keyword: keyword || null,
          advertiser_page: page || null,
          countries: country ? [country.toUpperCase()] : [],
          publisher_platforms: metaSurfaces,
          active_only: active,
          limit,
        };
      } else if (platform === "tiktok") {
        url = `${API}/scrape/tiktok`;
        body = {
          country: country.toUpperCase(),
          period,
          limit,
        };
      }
      const r = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok) setResult(`error: ${JSON.stringify(data)}`);
      else setResult(`queued task ${data.task_id}. Watch /queue.`);
    } catch (err) {
      setResult(`error: ${String(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold mb-2">New scrape</h1>
      <p className="text-sm text-muted mb-6">
        Enqueues a scrape task. The worker picks it up, ingests, scores, and
        auto-chains snapshot/analyze/embed.
      </p>

      <div className="flex gap-2 mb-6">
        {(["meta", "tiktok"] as Platform[]).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPlatform(p)}
            className={`px-4 py-2 rounded font-medium text-sm ${
              platform === p
                ? "bg-accent text-white"
                : "bg-panel border border-border text-muted hover:text-ink"
            }`}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="space-y-4 bg-panel border border-border rounded-lg p-5">
        {platform === "meta" && (
          <>
            <Row label="Keyword">
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder='e.g. "cold plunge"'
                className="w-full bg-bg border border-border rounded px-3 py-2"
              />
            </Row>
            <Row label="OR Page ID">
              <input
                type="text"
                value={page}
                onChange={(e) => setPage(e.target.value)}
                placeholder="numeric Facebook page id"
                className="w-full bg-bg border border-border rounded px-3 py-2"
              />
            </Row>
            <Row label="Surfaces (empty = all)">
              <div className="flex flex-wrap gap-2">
                {(["facebook", "instagram", "messenger", "threads", "audience_network"] as const).map(
                  (s) => {
                    const on = metaSurfaces.includes(s);
                    return (
                      <button
                        key={s}
                        type="button"
                        onClick={() =>
                          setMetaSurfaces(
                            on
                              ? metaSurfaces.filter((x) => x !== s)
                              : [...metaSurfaces, s],
                          )
                        }
                        className={`text-xs px-2.5 py-1.5 rounded font-mono ${
                          on
                            ? "bg-accent text-white"
                            : "bg-bg border border-border text-muted hover:text-ink"
                        }`}
                      >
                        {s}
                      </button>
                    );
                  },
                )}
              </div>
            </Row>
            <Row label="Active only">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
                className="w-4 h-4 accent-accent"
              />
            </Row>
          </>
        )}

        {platform === "tiktok" && (
          <Row label="Lookback period">
            <select
              value={period}
              onChange={(e) => setPeriod(parseInt(e.target.value, 10) as 7 | 30 | 120)}
              className="bg-bg border border-border rounded px-3 py-2"
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
            placeholder="US"
            maxLength={5}
            className="w-32 bg-bg border border-border rounded px-3 py-2 uppercase"
          />
        </Row>
        <Row label="Limit">
          <input
            type="number"
            value={limit}
            min={1}
            max={platform === "tiktok" ? 200 : 2000}
            onChange={(e) => setLimit(parseInt(e.target.value || "0", 10))}
            className="w-32 bg-bg border border-border rounded px-3 py-2"
          />
        </Row>

        <button
          type="submit"
          disabled={submitting || (platform === "meta" && !keyword && !page)}
          className="w-full py-2.5 rounded-md bg-accent text-white font-medium disabled:opacity-50"
        >
          {submitting ? "Submitting…" : "Enqueue scrape"}
        </button>
        {result && <div className="text-sm text-muted pt-2">{result}</div>}
      </form>
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
