"use client";
import { useRouter, useSearchParams } from "next/navigation";

const PLATFORMS = ["", "meta", "x", "tiktok", "google", "linkedin"];
const CREATIVE = ["", "video", "image", "carousel", "text"];
const HOOKS = [
  "",
  "curiosity",
  "authority",
  "fear",
  "problem_agitation",
  "transformation",
  "before_after",
  "social_proof",
  "contrarian",
  "pattern_interrupt",
  "listicle",
  "qa",
];

export function FilterBar() {
  const router = useRouter();
  const sp = useSearchParams();

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(sp.toString());
    if (value) next.set(key, value);
    else next.delete(key);
    router.push(`/?${next.toString()}`);
  };

  const Field = (props: {
    label: string;
    name: string;
    options: string[];
  }) => (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {props.label}
      <select
        value={sp.get(props.name) ?? ""}
        onChange={(e) => set(props.name, e.target.value)}
        className="bg-panel border border-border rounded-md px-2 py-1.5 text-ink"
      >
        {props.options.map((o) => (
          <option key={o} value={o}>
            {o || "any"}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="flex gap-3 items-end flex-wrap pb-4 border-b border-border mb-4">
      <Field label="Platform" name="platform" options={PLATFORMS} />
      <Field label="Creative" name="creative_type" options={CREATIVE} />
      <Field label="Hook" name="hook" options={HOOKS} />
      <label className="flex flex-col gap-1 text-xs text-muted">
        Min score
        <input
          type="number"
          min={0}
          max={100}
          step={5}
          defaultValue={sp.get("min_score") ?? ""}
          onBlur={(e) => set("min_score", e.target.value)}
          className="bg-panel border border-border rounded-md px-2 py-1.5 text-ink w-24"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Days active ≥
        <input
          type="number"
          min={0}
          defaultValue={sp.get("days_active_gte") ?? ""}
          onBlur={(e) => set("days_active_gte", e.target.value)}
          className="bg-panel border border-border rounded-md px-2 py-1.5 text-ink w-24"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Country
        <input
          type="text"
          placeholder="US"
          defaultValue={sp.get("country") ?? ""}
          onBlur={(e) => set("country", e.target.value.toUpperCase())}
          className="bg-panel border border-border rounded-md px-2 py-1.5 text-ink w-20 uppercase"
        />
      </label>
    </div>
  );
}
