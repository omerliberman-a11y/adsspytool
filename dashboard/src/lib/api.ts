export type Ad = {
  platform: string;
  ad_id: string;
  advertiser_name: string | null;
  advertiser_page_id: string | null;
  advertiser_url: string | null;
  first_seen: string | null;
  last_seen: string | null;
  days_active: number | null;
  countries: string[] | null;
  languages: string[] | null;
  placements: string[] | null;
  creative_type: string | null;
  media_urls: string[] | null;
  headline: string | null;
  primary_text: string | null;
  description: string | null;
  cta_text: string | null;
  cta_url: string | null;
  landing_url: string | null;
  variant_count: number | null;
  reach_band: string | null;
  winner_score: number | null;
  hook_type: string | null;
  awareness_stage: number | null;
  copy_framework: string | null;
  ai_hook: string | null;
  ai_angle: string | null;
  ai_offer: string | null;
  ai_summary: string | null;
  ai_rewritten_copy: string[] | null;
};

export type AdListResp = { count: number; items: Ad[] };

export type Stats = {
  ads: {
    total: number;
    per_platform: Record<string, number>;
    per_creative_type: Record<string, number>;
    per_hook_type: Record<string, number>;
    winner_score_buckets: Record<string, number>;
  };
  ai_today: { total: number; per_provider: Record<string, number> };
  scrape_runs_today: number;
  tasks_by_status: Record<string, number>;
};

export type Task = {
  id: number;
  kind: string;
  status: string;
  priority: number;
  attempts: number;
  max_attempts: number;
  payload: Record<string, unknown> | null;
  error: string | null;
  scheduled_for: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

/**
 * Browser-side API base. Client-side fetches use `/api/*` so they hit the same
 * origin as the dashboard, which Next.js rewrites to the backend (see
 * `next.config.ts`). This lets a single Cloudflare/ngrok tunnel serve both
 * pages and API publicly without exposing the backend port separately.
 *
 * Server-side renders (in `page.tsx` server components) still hit the backend
 * directly via `process.env.NEXT_PUBLIC_API_BASE`.
 */
export const CLIENT_API_BASE = "/api";

export const fetcher = async <T,>(url: string): Promise<T> => {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
};
