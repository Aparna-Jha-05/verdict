"use client";

import { CheckCircle2, Download } from "lucide-react";
import { useState } from "react";
import { useProcess } from "../../context/ProcessContext";

export default function ApproveBar({ reviewed }: { reviewed: boolean }) {
  const { extraction, approve, approved } = useProcess();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doApprove = async () => {
    setBusy(true);
    setError(null);
    try {
      await approve();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  };

  const downloadCsv = () => {
    if (!approved) return;
    const blob = new Blob([approved.csv_row], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `invoice_${extraction?.invoice_number.value || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (approved) {
    return (
      <div className="panel animate-pop border-green/40 bg-green/10">
        <div className="flex items-center gap-2 text-green">
          <CheckCircle2 className="h-5 w-5" />
          <h3 className="text-[15px] font-bold">Approved &amp; logged</h3>
        </div>
        <p className="mt-2 text-sm">{approved.mock_action.message}</p>
        <p className="mt-1 text-sm text-muted">
          Ledger id #{approved.ledger_id}. This invoice now blocks future duplicates.
        </p>
        <button onClick={downloadCsv} className="btn btn-ghost mt-3 text-xs">
          <Download className="h-3.5 w-3.5" /> Download CSV row
        </button>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted">
          {reviewed
            ? "You've reviewed validation and fraud. Ready to approve."
            : "Review the validation and fraud panels before approving."}
        </p>
        <button
          onClick={doApprove}
          disabled={!reviewed || busy}
          className="btn btn-primary"
        >
          {busy ? "Approving…" : "Approve → queue for payment"}
        </button>
      </div>
      {error && (
        <div className="mt-2 rounded-lg border border-red/50 bg-red/10 px-3 py-2 text-xs text-red">
          {error}
        </div>
      )}
    </div>
  );
}
