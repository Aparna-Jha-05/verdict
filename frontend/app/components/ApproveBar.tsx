"use client";

import { useState } from "react";
import { approveInvoice } from "../lib/api";
import type { ApproveResponse, Extraction } from "../lib/types";

interface Props {
  extraction: Extraction;
  reviewed: boolean; // human has seen validation + fraud panels
  onApproved: () => void;
}

export default function ApproveBar({ extraction, reviewed, onApproved }: Props) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ApproveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const approve = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await approveInvoice(extraction);
      setResult(r);
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  };

  const downloadCsv = () => {
    if (!result) return;
    const blob = new Blob([result.csv_row], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoice_${extraction.invoice_number.value || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (result) {
    return (
      <div className="panel">
        <div className="success-card">
          <h3>✓ Approved &amp; logged</h3>
          <p>{result.mock_action.message}</p>
          <p style={{ color: "var(--muted)" }}>
            Ledger id #{result.ledger_id}. This invoice now blocks future
            duplicates.
          </p>
          <button
            className="btn btn-ghost"
            style={{ marginTop: 10 }}
            onClick={downloadCsv}
          >
            ⬇ Download CSV row
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="approve-bar">
        <div className="approve-hint">
          {reviewed
            ? "You've reviewed validation and fraud. Ready to approve."
            : "Review the validation and fraud panels before approving."}
        </div>
        <button
          className="btn btn-primary"
          disabled={!reviewed || busy}
          onClick={approve}
        >
          {busy ? "Approving…" : "Approve → queue for payment"}
        </button>
      </div>
      {error && (
        <div className="error-banner" style={{ marginTop: 10 }}>
          {error}
        </div>
      )}
    </div>
  );
}
