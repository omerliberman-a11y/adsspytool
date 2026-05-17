import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Item = {
  platform: string;
  ad_id: string;
  advertiser_name: string | null;
  headline: string | null;
  winner_score: number | null;
  media_urls: string[] | null;
  source_url: string | null;
  final_url: string | null;
};

async function load(domain: string): Promise<{ domain: string; count: number; items: Item[] }> {
  const r = await fetch(
    `${API}/sources/by-domain/${encodeURIComponent(domain)}?limit=200`,
    { cache: "no-store" },
  );
  if (!r.ok) return { domain, count: 0, items: [] };
  return r.json();
}

type Props = { params: Promise<{ domain: string }> };

export default async function DomainPage({ params }: Props) {
  const { domain } = await params;
  const data = await load(decodeURIComponent(domain));

  return (
    <div>
      <div className="mb-4">
        <Link href="/sources" className="text-sm text-muted hover:text-ink">
          ← All sources
        </Link>
      </div>
      <h1 className="text-2xl font-semibold mb-1">{data.domain}</h1>
      <div className="text-sm text-muted mb-6">{data.count} ads point here</div>

      {data.items.length === 0 ? (
        <div className="text-muted">No ads.</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {data.items.map((a) => (
            <Link
              key={`${a.platform}/${a.ad_id}`}
              href={`/ads/${a.platform}/${a.ad_id}`}
              className="block bg-panel border border-border rounded-lg overflow-hidden hover:border-accent transition"
            >
              <div className="aspect-square bg-black/40">
                {a.media_urls?.[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={a.media_urls[0]}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full grid place-items-center text-muted text-xs uppercase">
                    no media
                  </div>
                )}
              </div>
              <div className="p-3 text-xs">
                <div className="flex justify-between mb-1">
                  <span className="text-muted">{a.platform}</span>
                  <span className="font-mono">{a.winner_score ?? "—"}</span>
                </div>
                <div className="font-medium truncate">{a.advertiser_name ?? "?"}</div>
                <div className="text-muted truncate mt-0.5">{a.headline ?? ""}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
