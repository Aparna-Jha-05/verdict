"use client";

import { AlertTriangle, CheckCircle2, FileScan, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { useProcess } from "../../context/ProcessContext";
import { getStats } from "../../lib/api";
import type { Stats } from "../../lib/types";

export default function SummaryRow() {
  const { bump } = useProcess();
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => setStats(null));
  }, [bump]);

  const tiles = [
    { label: "Processed", value: stats?.processed ?? "—", icon: FileScan, tint: "text-violet" },
    { label: "Approved", value: stats?.approved ?? "—", icon: CheckCircle2, tint: "text-green" },
    { label: "Flagged", value: stats?.flagged ?? "—", icon: AlertTriangle, tint: "text-red" },
    {
      label: "Escalation rate",
      value: stats ? `${Math.round(stats.escalation_rate * 100)}%` : "—",
      icon: Zap,
      tint: "text-gold",
    },
  ];

  const dist = stats?.confidence_distribution;
  const total = dist ? dist.high + dist.medium + dist.low : 0;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => {
        const Icon = t.icon;
        return (
          <div key={t.label} className="stat-tile">
            <div className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wide text-muted">{t.label}</span>
              <Icon className={`h-4 w-4 ${t.tint}`} />
            </div>
            <div className="mt-2 text-3xl font-extrabold tracking-tight">{t.value}</div>
          </div>
        );
      })}

      {dist && (
        <div className="stat-tile col-span-2 lg:col-span-4">
          <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide text-muted">
            <span>Confidence distribution</span>
            <span>{total} extraction{total === 1 ? "" : "s"}</span>
          </div>
          {total === 0 ? (
            <p className="text-xs text-muted">No extractions yet — process an invoice to populate.</p>
          ) : (
            <div className="flex h-3 overflow-hidden rounded-full bg-inset">
              <div className="bg-green" style={{ width: `${(dist.high / total) * 100}%` }} title={`High: ${dist.high}`} />
              <div className="bg-amber" style={{ width: `${(dist.medium / total) * 100}%` }} title={`Medium: ${dist.medium}`} />
              <div className="bg-red" style={{ width: `${(dist.low / total) * 100}%` }} title={`Low: ${dist.low}`} />
            </div>
          )}
          {total > 0 && (
            <div className="mt-2 flex gap-4 text-[11px] text-muted">
              <span><span className="dot bg-green mr-1 align-middle" />High {dist.high}</span>
              <span><span className="dot bg-amber mr-1 align-middle" />Medium {dist.medium}</span>
              <span><span className="dot bg-red mr-1 align-middle" />Low {dist.low}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
