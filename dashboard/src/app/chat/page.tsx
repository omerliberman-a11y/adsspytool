"use client";
import { useRef, useState } from "react";
import { CLIENT_API_BASE } from "@/lib/api";

const API = CLIENT_API_BASE;

type Role = "user" | "assistant";
type Msg = { role: Role; content: string; toolCalls?: ToolCall[]; latencyMs?: number };
type ToolCall = { name: string; args: Record<string, unknown>; result_len: number };

const SUGGESTIONS = [
  "Show me the top 5 winners on TikTok",
  "What hooks are working best in US?",
  "Which advertisers have the most ads?",
  "Top destination domains across all ads",
  "Are there any ClickBank affiliates in our data?",
  "Hook breakdown for tiktok",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(text: string) {
    const user: Msg = { role: "user", content: text };
    const next = [...messages, user];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          messages: next.map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      const d = await r.json();
      if (!r.ok) {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: `Error: ${d.detail ?? "unknown"}` },
        ]);
      } else {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            content: d.reply || "(empty reply)",
            toolCalls: d.tool_calls,
            latencyMs: d.latency_ms,
          },
        ]);
      }
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Chat with your data</h1>
        <p className="text-sm text-muted mt-1">
          Groq Llama 3.3 70B with tool-use over the ads DB. Read-only — answers come from real
          queries.
        </p>
      </div>

      {messages.length === 0 && (
        <div className="bg-panel border border-border rounded-lg p-5 mb-6">
          <div className="text-xs uppercase tracking-wider text-muted mb-3">Try</div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-sm px-3 py-2 rounded bg-bg border border-border text-muted hover:text-ink hover:border-accent"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4 mb-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-4 py-2.5 text-sm ${
                m.role === "user"
                  ? "bg-accent text-white"
                  : "bg-panel border border-border"
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.toolCalls && m.toolCalls.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border text-[10px] text-muted font-mono">
                  {m.toolCalls.map((tc, j) => (
                    <div key={j} className="truncate">
                      🔧 {tc.name}({Object.keys(tc.args).join(", ")}) → {tc.result_len}B
                    </div>
                  ))}
                  {m.latencyMs && <div className="mt-1">{m.latencyMs}ms</div>}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-panel border border-border px-4 py-2.5 text-sm text-muted">
              thinking…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim() && !busy) send(input.trim());
        }}
        className="flex gap-2 sticky bottom-0 bg-bg pt-4"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          placeholder="Ask anything about the ads…"
          className="flex-1 bg-panel border border-border rounded px-4 py-3"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="px-5 py-3 rounded bg-accent text-white font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
