"use client";
import Link from "next/link";
import type { Ad } from "@/lib/api";

function scoreColor(score: number | null): string {
  if (score === null || score === undefined) return "text-muted";
  if (score >= 80) return "text-good";
  if (score >= 60) return "text-warn";
  if (score >= 40) return "text-ink";
  return "text-muted";
}

export function AdCard({ ad }: { ad: Ad }) {
  const hero = ad.media_urls?.[0];
  const isVideo = ad.creative_type === "video";
  // Hero is whatever's first in media_urls. For TikTok the cover image comes first
  // even when creative_type is video, so detect the actual hero MIME by URL signal.
  const heroIsImage = !!hero && /\.(jpe?g|png|webp|gif|avif)(\?|#|$)/i.test(hero);
  const heroIsVideo = !!hero && /\.(mp4|webm|mov|m4v)(\?|#|$)/i.test(hero);
  const videoSrc = isVideo
    ? (ad.media_urls || []).find((u) => /\.(mp4|webm|mov)(\?|#|$)/i.test(u)) ?? null
    : null;

  return (
    <Link
      href={`/ads/${ad.platform}/${ad.ad_id}`}
      className="group block bg-panel border border-border rounded-lg overflow-hidden hover:border-accent transition"
    >
      <div className="aspect-square bg-black/40 relative">
        {hero && (heroIsImage || !heroIsVideo) ? (
          // Render as image — cover thumbnail for video, or plain image
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={hero}
            alt={ad.headline ?? ad.advertiser_name ?? ""}
            className="w-full h-full object-cover"
          />
        ) : hero && heroIsVideo ? (
          <video
            src={hero}
            className="w-full h-full object-cover"
            muted
            loop
            playsInline
            onMouseOver={(e) => (e.currentTarget as HTMLVideoElement).play()}
            onMouseOut={(e) => {
              const v = e.currentTarget as HTMLVideoElement;
              v.pause();
              v.currentTime = 0;
            }}
          />
        ) : (
          <div className="w-full h-full grid place-items-center text-muted text-xs uppercase tracking-wider">
            {ad.creative_type ?? "no media"}
          </div>
        )}
        {isVideo && videoSrc && (
          <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-ink text-[10px] font-mono uppercase tracking-wider">
            ▶ video
          </div>
        )}

        <div className="absolute top-2 right-2 flex items-center gap-1">
          <span
            className={`px-2 py-0.5 rounded text-xs font-mono ${scoreColor(ad.winner_score)} bg-black/60`}
          >
            {ad.winner_score ?? "—"}
          </span>
        </div>

        {ad.hook_type && (
          <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-black/70 text-ink">
            {ad.hook_type}
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="text-xs text-muted truncate">{ad.advertiser_name ?? "?"}</div>
        <div className="text-sm font-medium mt-0.5 line-clamp-2 min-h-[2.5em]">
          {ad.ai_hook ?? ad.headline ?? ad.primary_text ?? "(no copy)"}
        </div>
        <div className="text-xs text-muted mt-2 flex gap-3">
          <span>{ad.days_active ?? "?"}d</span>
          <span>·</span>
          <span>{ad.variant_count ?? "?"}v</span>
          <span>·</span>
          <span>{ad.creative_type ?? "?"}</span>
        </div>
      </div>
    </Link>
  );
}
