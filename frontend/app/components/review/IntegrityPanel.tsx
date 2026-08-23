"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { Extraction, IntegrityResult } from "../../lib/types";
import QueryDraft from "./QueryDraft";

const CHECK_LABELS: Record<string, string> = {
  pdf_metadata: "Document metadata forensics",
  account_change: "Sensitive detail change",
  exact_duplicate: "Exact duplicate",
  semantic_duplicate: "Semantic near-duplicate",
};

const SEV_CLS: Record<string, string> = {
  high: "border-l-red bg-red/10",
  medium: "border-l-amber bg-amber/10",
  low: "border-l-violet bg-violet/10",
  info: "border-l-muted bg-white/[0.03]",
};

export default function IntegrityPanel({
  integrity,
  label,
  domain,
  extraction,
}: {
  integrity: IntegrityResult;
  label: string;
  domain: string;
  extraction: Extraction;
}) {
  const actionable = integrity.flags.filter((f) => f.severity !== "info");
  const showDraft = actionable.some(
    (f) => f.check === "account_change" || f.severity === "high"
  );

  return (
    <div className="panel">
      <div className="panel-title">
        {actionable.length === 0 ? (
          <ShieldCheck className="h-4 w-4 text-green" />
        ) : (
          <ShieldAlert className="h-4 w-4 text-red" />
        )}
        {label}
        <span className="font-normal normal-case tracking-normal text-muted">
          {actionable.length === 0
            ? "· no flags raised"
            : `· ${actionable.length} flag${actionable.length > 1 ? "s" : ""} for review`}
        </span>
      </div>

      {integrity.flags.length === 0 && (
        <p className="px-1 py-2 text-[13px] text-green">
          No integrity signals in this pass. (Never a guarantee — only that these
          deterministic checks found nothing to flag.)
        </p>
      )}

      <div className="space-y-2">
        {integrity.flags.map((f, i) => (
          <div key={i} className={`rounded-lg border-l-[3px] p-2.5 ${SEV_CLS[f.severity]}`}>
            <div className="flex items-center gap-2 text-[12px] font-semibold">
              {CHECK_LABELS[f.check] || f.check}
              <span className="rounded bg-black/30 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-gold">
                {f.severity === "info" ? "note" : "flag for review"}
              </span>
            </div>
            <div className="mt-1 text-xs text-muted">{f.reason}</div>
          </div>
        ))}
      </div>

      {showDraft && <QueryDraft domain={domain} extraction={extraction} />}
    </div>
  );
}
