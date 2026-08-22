"use client";

import { AlertTriangle, CheckCircle2, FileScan, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useProcess } from "../../context/ProcessContext";
import { getActivity } from "../../lib/api";
import type { ActivityItem } from "../../lib/types";

const ICONS: Record<string, { icon: typeof FileScan; tint: string }> = {
  processed: { icon: FileScan, tint: "text-violet" },
  approved: { icon: CheckCircle2, tint: "text-green" },
  flagged: { icon: AlertTriangle, tint: "text-red" },
  escalated: { icon: Zap, tint: "text-gold" },
};

export function timeAgo(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function RecentActivity() {
  const { bump } = useProcess();
  const [items, setItems] = useState<ActivityItem[]>([]);

  useEffect(() => {
    getActivity(8).then(setItems).catch(() => setItems([]));
  }, [bump]);

  return (
    <div className="panel">
      <div className="panel-title">
        Recent Activity
        <Link href="/audit" className="ml-auto text-[11px] font-normal normal-case tracking-normal text-violet hover:underline">
          View all →
        </Link>
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">
          Nothing yet. Process an invoice to start the audit trail.
        </p>
      ) : (
        <div className="space-y-1">
          {items.map((a) => {
            const { icon: Icon, tint } = ICONS[a.type] || ICONS.processed;
            return (
              <div key={a.id} className="flex items-start gap-3 rounded-lg px-1 py-2">
                <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tint}`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[13px]">{a.summary}</p>
                  <p className="text-[11px] text-muted">
                    {a.vendor_name && <span>{a.vendor_name} · </span>}
                    {a.invoice_number && <span>{a.invoice_number} · </span>}
                    {timeAgo(a.ts)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
