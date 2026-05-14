import { FilterBar } from "@/components/FilterBar";
import { AdCard } from "@/components/AdCard";
import type { Ad, AdListResp } from "@/lib/api";

async function loadAds(searchParams: Record<string, string | string[] | undefined>) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(searchParams)) {
    if (typeof v === "string" && v) qs.set(k === "hook" ? "hook_type" : k, v);
  }
  if (!qs.has("limit")) qs.set("limit", "60");
  const url = `${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/ads?${qs}`;
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) return { count: 0, items: [] as Ad[] };
  return (await r.json()) as AdListResp;
}

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function Home({ searchParams }: PageProps) {
  const sp = await searchParams;
  const data = await loadAds(sp);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-2xl font-semibold">Winners</h1>
        <span className="text-sm text-muted">{data.count} ads</span>
      </div>
      <FilterBar />
      {data.items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {data.items.map((ad) => (
            <AdCard key={`${ad.platform}/${ad.ad_id}`} ad={ad} />
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="border border-dashed border-border rounded-lg p-12 text-center text-muted">
      <div className="text-lg text-ink mb-2">No ads yet</div>
      <div className="text-sm">
        Run a scrape from the CLI or hit{" "}
        <code className="text-accent">POST /scrape/meta</code>.
      </div>
    </div>
  );
}
