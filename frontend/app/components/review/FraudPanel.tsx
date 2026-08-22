"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import type { Extraction, FraudResult } from "../../lib/types";
import VendorQueryDraft from "./VendorQueryDraft";

const CHECK_LABELS: Record<string, string> = {
  pdf_metadata: "PDF metadata forensics",
  bank_detail_change: "Vendor bank-detail change",
  exact_duplicate: "Exact duplicate",
  semantic_duplicate: "Semantic near-duplicate",
};

const SEV_CLS: Record<string, string> = {
  high: "border-l-red bg-red/10",
  medium: "border-l-amber bg-amber/10",
  low: "border-l-violet bg-violet/10",
  info: "border-l-muted bg-white/[0.03]",
};

export default function FraudPanel({
  fraud,
  extraction,
}: {
  fraud: FraudResult;
  extraction: Extraction;
}) {
  const actionable = fraud.flags.filter((f) => f.severity !== "info");
  const showDraft = actionable.some(
    (f) => f.check === "bank_detail_change" || f.severity === "high"
  );

  return (
    <div className="panel">
      <div className="panel-title">
        {actionable.length === 0 ? (
          <ShieldCheck className="h-4 w-4 text-green" />
        ) : (
          <ShieldAlert className="h-4 w-4 text-red" />
        )}
        Fraud &amp; Tamper Review
        <span className="font-normal normal-case tracking-normal text-muted">
          {actionable.length === 0
            ? "· no flags raised"
            : `· ${actionable.length} flag${actionable.length > 1 ? "s" : ""} for review`}
        </span>
      </div>

      {fraud.flags.length === 0 && (
        <p className="px-1 py-2 text-[13px] text-green">
          No fraud signals in this pass. (Never a guarantee of authenticity — only that these
          deterministic checks found nothing to flag.)
        </p>
      )}

      <div className="space-y-2">
        {fraud.flags.map((f, i) => (
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

      {showDraft && <VendorQueryDraft extraction={extraction} />}
    </div>
  );
}
