"use client";

import { AlertTriangle, CheckCircle2, FileScan, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { timeAgo } from "../components/dashboard/RecentActivity";
import { useProcess } from "../context/ProcessContext";
import { getActivity } from "../lib/api";
import type { ActivityItem } from "../lib/types";

const ICONS: Record<string, { icon: typeof FileScan; tint: string }> = {
  processed: { icon: FileScan, tint: "text-violet" },
  approved: { icon: CheckCircle2, tint: "text-green" },
  flagged: { icon: AlertTriangle, tint: "text-red" },
  escalated: { icon: Zap, tint: "text-gold" },
};

const FILTERS = ["all", "processed", "flagged", "approved", "escalated"] as const;

export default function AuditPage() {
  const { bump } = useProcess();
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");

  useEffect(() => {
    setLoading(true);
    getActivity(200)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [bump]);

  const shown = filter === "all" ? items : items.filter((i) => i.type === filter);

  return (
    <div className="panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="panel-title mb-0">
          Activity Trail
          <span className="font-normal normal-case tracking-normal text-muted">
            · {items.length} events
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-2.5 py-1 text-xs capitalize transition-colors ${
                filter === f ? "bg-violet/15 text-text" : "text-muted hover:text-text"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="py-10 text-center text-muted">Loading activity…</p>
      ) : shown.length === 0 ? (
        <p className="py-10 text-center text-muted">No events.</p>
      ) : (
        <div className="relative space-y-0 pl-4">
          <div className="absolute bottom-2 left-[7px] top-2 w-px bg-line/20" />
          {shown.map((a) => {
            const { icon: Icon, tint } = ICONS[a.type] || ICONS.processed;
            return (
              <div key={a.id} className="relative flex gap-3 py-2.5">
                <div className="absolute -left-4 top-3 grid h-3.5 w-3.5 place-items-center rounded-full bg-surface">
                  <Icon className={`h-3 w-3 ${tint}`} />
                </div>
                <div className="min-w-0 flex-1 pl-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold capitalize ${tint}`}>{a.type}</span>
                    <span className="text-[11px] text-muted">{timeAgo(a.ts)}</span>
                  </div>
                  <p className="mt-0.5 text-[13px]">{a.summary}</p>
                  {(a.vendor_name || a.invoice_number) && (
                    <p className="text-[11px] text-muted">
                      {a.vendor_name}
                      {a.vendor_name && a.invoice_number ? " · " : ""}
                      {a.invoice_number}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
