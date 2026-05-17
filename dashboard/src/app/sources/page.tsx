import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type DomainRow = {
  domain: string;
  ad_count: number;
  advertiser_count: number;
  platforms: string[];
};

type AffiliateRow = {
  network: string;
  ad_count: number;
};

async function loadDomains(): Promise<{ count: number; items: DomainRow[] }> {
  const r = await fetch(`${API}/sources/domains?limit=200`, { cache: "no-store" });
  if (!r.ok) return { count: 0, items: [] };
  return r.json();
}

async function loadAffiliates(): Promise<{ count: number; items: AffiliateRow[] }> {
  const r = await fetch(`${API}/sources/affiliate-networks`, { cache: "no-store" });
  if (!r.ok) return { count: 0, items: [] };
  return r.json();
}

export default async function SourcesPage() {
  const [domains, affiliates] = await Promise.all([loadDomains(), loadAffiliates()]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Link sources</h1>
        <p className="text-sm text-muted mt-1">
          Where ads point to. Resolved destinations across all platforms — the actual product page
          after redirects + affiliate networks unmasked.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-3">Top destination domains</h2>
          {domains.items.length === 0 ? (
            <EmptyDomains />
          ) : (
            <div className="bg-panel border border-border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-bg text-muted text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left px-3 py-2">Domain</th>
                    <th className="text-right px-3 py-2">Ads</th>
                    <th className="text-right px-3 py-2">Advertisers</th>
                    <th className="text-left px-3 py-2">Platforms</th>
                  </tr>
                </thead>
                <tbody>
                  {domains.items.map((d) => (
                    <tr key={d.domain} className="border-t border-border">
                      <td className="px-3 py-2 font-mono">
                        <Link
                          href={`/sources/${encodeURIComponent(d.domain)}`}
                          className="text-ink hover:text-accent"
                        >
                          {d.domain}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-right font-mono">{d.ad_count}</td>
                      <td className="px-3 py-2 text-right font-mono">{d.advertiser_count}</td>
                      <td className="px-3 py-2">
                        {(d.platforms || []).map((p) => (
                          <span
                            key={p}
                            className="mr-1 px-1.5 py-0.5 rounded bg-bg text-muted font-mono text-[10px]"
                          >
                            {p}
                          </span>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-3">Affiliate networks detected</h2>
          {affiliates.items.length === 0 ? (
            <div className="text-muted text-sm bg-panel border border-border rounded-lg p-4">
              None detected yet. Networks tracked: ClickBank, Digistore24, MaxBounty, BuyGoods,
              WarriorPlus, JVZoo, CJ, ShareASale, Awin, Impact, Refersion, Rakuten, Skimlinks.
            </div>
          ) : (
            <div className="bg-panel border border-border rounded-lg divide-y divide-border">
              {affiliates.items.map((a) => (
                <div key={a.network} className="px-3 py-2 flex justify-between text-sm">
                  <span className="font-mono text-warn">{a.network}</span>
                  <span className="font-mono">{a.ad_count} ad{a.ad_count === 1 ? "" : "s"}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyDomains() {
  return (
    <div className="border border-dashed border-border rounded-lg p-12 text-center text-muted">
      <div className="text-ink mb-2">No links resolved yet.</div>
      <div className="text-sm">
        Run <code className="text-accent">POST /admin/resolve-links/batch</code> to resolve ads with
        cta_urls. New ingests auto-resolve as part of the pipeline.
      </div>
    </div>
  );
}
