"use client";

import { Check, Copy, Mail } from "lucide-react";
import { useState } from "react";
import { draftQuery } from "../../lib/api";
import type { Extraction } from "../../lib/types";

export default function QueryDraft({
  domain,
  extraction,
}: {
  domain: string;
  extraction: Extraction;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const generate = async () => {
    setBusy(true);
    try {
      const r = await draftQuery(domain, extraction);
      setDraft(r.draft);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!draft) return;
    await navigator.clipboard.writeText(draft);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!draft) {
    return (
      <button onClick={generate} disabled={busy} className="btn btn-ghost mt-1 w-full text-xs">
        <Mail className="h-3.5 w-3.5" />
        {busy ? "Drafting…" : "Draft verification query"}
      </button>
    );
  }

  return (
    <div className="mt-2 rounded-xl border border-line/20 bg-inset/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-violet">
          Verification draft
        </span>
        <button onClick={copy} className="flex items-center gap-1 text-[11px] text-muted hover:text-text">
          {copied ? <Check className="h-3.5 w-3.5 text-green" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-text/90">
        {draft}
      </pre>
    </div>
  );
}
