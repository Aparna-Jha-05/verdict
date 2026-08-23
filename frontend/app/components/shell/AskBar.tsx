"use client";

import { ArrowRight, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { askAssistant, type AskResponse } from "../../lib/api";

const DEFAULT_CHIPS = [
  "How many items did we flag?",
  "What's my credit balance?",
  "How does the anomaly check work?",
  "What's our unique selling point?",
];

export default function AskBar() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AskResponse | null>(null);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text) return;
    setQ(text);
    setBusy(true);
    setRes(null);
    try {
      setRes(await askAssistant(text));
    } catch (e) {
      setRes({ answer: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      setBusy(false);
    }
  };

  const chips = res?.suggestions?.length ? res.suggestions : DEFAULT_CHIPS;

  return (
    <div className="rounded-2xl border border-line/20 bg-gradient-to-br from-violet/[0.1] to-transparent p-4 backdrop-blur-xl">
      <div className="flex items-center gap-2">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-violet to-gold text-on-accent">
          <Sparkles className="h-4 w-4" />
        </span>
        <form
          className="flex flex-1 items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            ask(q);
          }}
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask Verdict anything — your flags, credits, or how a check works…"
            className="min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted"
          />
          {q && (
            <button
              type="button"
              onClick={() => { setQ(""); setRes(null); }}
              className="grid h-7 w-7 place-items-center rounded-lg text-muted hover:text-text"
              aria-label="Clear"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <button
            type="submit"
            disabled={busy || !q.trim()}
            className="btn btn-primary h-9 px-3 text-sm disabled:opacity-50"
          >
            {busy ? "…" : "Ask"}
          </button>
        </form>
      </div>

      {res && (
        <div className="mt-3 animate-pop rounded-xl border border-line/20 bg-card/70 p-3.5">
          <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-violet">
            <Sparkles className="h-3 w-3" /> Verdict AI
          </div>
          <p className="text-sm leading-relaxed text-text">{res.answer}</p>
          {res.nav && (
            <button
              onClick={() => router.push(res.nav!)}
              className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-gold hover:underline"
            >
              Open {res.nav.replace("/", "") || "dashboard"} <ArrowRight className="h-3 w-3" />
            </button>
          )}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {chips.map((c) => (
          <button key={c} onClick={() => ask(c)} disabled={busy} className="chip">
            {c}
          </button>
        ))}
      </div>
    </div>
  );
}
