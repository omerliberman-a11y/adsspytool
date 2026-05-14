"use client";
import { useState } from "react";
import { CLIENT_API_BASE } from "@/lib/api";

const API = CLIENT_API_BASE;

export default function ScrapePage() {
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState("");
  const [country, setCountry] = useState("US");
  const [limit, setLimit] = useState(200);
  const [active, setActive] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/scrape/meta`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          keyword: keyword || null,
          advertiser_page: page || null,
          countries: country ? [country.toUpperCase()] : [],
          active_only: active,
          limit,
        }),
      });
      const data = await r.json();
      if (!r.ok) {
        setResult(`error: ${JSON.stringify(data)}`);
      } else {
        setResult(`queued task ${data.task_id}. Watch /queue.`);
      }
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
        Enqueues a <code className="text-accent">scrape_meta</code> task. The worker will pick it
        up, hit the Meta Graph API, normalize, score, and auto-enqueue snapshot/analyze/embed
        downstream.
      </p>
      <form onSubmit={submit} className="space-y-4 bg-panel border border-border rounded-lg p-5">
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
            max={2000}
            onChange={(e) => setLimit(parseInt(e.target.value || "0", 10))}
            className="w-32 bg-bg border border-border rounded px-3 py-2"
          />
        </Row>
        <Row label="Active only">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
            className="w-4 h-4 accent-accent"
          />
        </Row>
        <button
          type="submit"
          disabled={submitting || (!keyword && !page)}
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
