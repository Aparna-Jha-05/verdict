"use client";

import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useProcess } from "../context/ProcessContext";
import { getLog } from "../lib/api";
import type { LedgerRecord } from "../lib/types";

export default function LedgerPage() {
  const { bump } = useProcess();
  const [rows, setRows] = useState<LedgerRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    setLoading(true);
    getLog()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [bump]);

  const filtered = useMemo(() => {
    const s = q.toLowerCase();
    return rows.filter(
      (r) =>
        r.party.toLowerCase().includes(s) ||
        r.ref.toLowerCase().includes(s) ||
        r.domain.toLowerCase().includes(s)
    );
  }, [rows, q]);

  return (
    <div className="panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="panel-title mb-0">
          Approved Records
          <span className="font-normal normal-case tracking-normal text-muted">
            · {rows.length} in ledger
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-line/20 px-2.5 py-1.5">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search party, ref, domain"
            className="w-40 bg-transparent text-xs outline-none placeholder:text-muted sm:w-56"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-sm">
          <thead>
            <tr className="text-[11px] uppercase text-muted">
              {["Domain", "Reference", "Party", "Date", "Amount", "Approved"].map((h) => (
                <th key={h} className="border-b border-line/20 px-3 py-2 text-left font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-10 text-center text-muted">Loading ledger…</td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-10 text-center text-muted">
                  {rows.length === 0 ? "No approved records yet." : "No matches."}
                </td>
              </tr>
            ) : (
              filtered.map((r) => (
                <tr key={r.id} className="hover:bg-violet/[0.05]">
                  <td className="border-b border-line/10 px-3 py-2.5">
                    <span className="rounded-md bg-violet/10 px-2 py-0.5 text-[11px] capitalize text-violet">
                      {r.domain}
                    </span>
                  </td>
                  <td className="border-b border-line/10 px-3 py-2.5 font-mono text-xs">{r.ref || "—"}</td>
                  <td className="border-b border-line/10 px-3 py-2.5">{r.party || "—"}</td>
                  <td className="border-b border-line/10 px-3 py-2.5 text-muted">{r.doc_date || "—"}</td>
                  <td className="border-b border-line/10 px-3 py-2.5 tabular-nums">
                    {r.amount === null ? "—" : r.amount.toFixed(2)}
                  </td>
                  <td className="border-b border-line/10 px-3 py-2.5 text-muted">
                    {r.approved_at ? new Date(r.approved_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
