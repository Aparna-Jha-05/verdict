"use client";

import type { FraudResult } from "../lib/types";

const CHECK_LABELS: Record<string, string> = {
  pdf_metadata: "PDF metadata forensics",
  bank_detail_change: "Vendor bank-detail change",
  exact_duplicate: "Exact duplicate",
  semantic_duplicate: "Semantic near-duplicate",
};

export default function FraudPanel({ fraud }: { fraud: FraudResult }) {
  // Actionable flags (high/medium/low) vs info notes.
  const actionable = fraud.flags.filter((f) => f.severity !== "info");
  return (
    <div className="panel">
      <h2>
        Fraud &amp; Tamper Review{" "}
        <span className="count">
          {actionable.length === 0
            ? "· no flags raised"
            : `· ${actionable.length} flag${actionable.length > 1 ? "s" : ""} for review`}
        </span>
      </h2>

      {fraud.flags.length === 0 && (
        <div className="clean-note">
          No fraud signals in this pass. (Never a guarantee of authenticity —
          only that these deterministic checks found nothing to flag.)
        </div>
      )}

      {fraud.flags.map((f, i) => (
        <div key={i} className={`flag-row ${f.severity}`}>
          <div>
            <div className="flag-head">
              {CHECK_LABELS[f.check] || f.check}
              <span className="flag-tag">
                {f.severity === "info" ? "note" : "flag for review"}
              </span>
            </div>
            <div className="flag-reason">{f.reason}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
