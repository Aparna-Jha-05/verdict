"use client";

import { Activity } from "lucide-react";
import type { AnomalyResult } from "../../lib/types";

const LEVEL: Record<string, { tint: string; bar: string; label: string }> = {
  normal: { tint: "text-green", bar: "bg-green", label: "Normal" },
  elevated: { tint: "text-amber", bar: "bg-amber", label: "Elevated" },
  high: { tint: "text-red", bar: "bg-red", label: "High" },
  learning: { tint: "text-muted", bar: "bg-muted", label: "Learning" },
};

export default function AnomalyPanel({ anomaly }: { anomaly: AnomalyResult }) {
  const meta = LEVEL[anomaly.level] || LEVEL.normal;
  const pct = Math.round(anomaly.score * 100);

  return (
    <div className="panel">
      <div className="panel-title">
        <Activity className="h-4 w-4 text-violet" />
        Anomaly Signal
        <span className="rounded bg-violet/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-violet">
          ML
        </span>
      </div>

      <div className="flex items-baseline gap-3">
        <span className={`text-sm font-semibold ${meta.tint}`}>{meta.label}</span>
        {anomaly.level !== "learning" && (
          <span className="font-mono text-xs text-muted">outlier score {pct}/100</span>
        )}
      </div>

      {anomaly.level !== "learning" && (
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-inset">
          <div className={`h-full ${meta.bar}`} style={{ width: `${Math.max(pct, 3)}%` }} />
        </div>
      )}

      <p className="mt-2 text-xs text-muted">{anomaly.reason}</p>

      {anomaly.features.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-line/15 pt-2 text-[11px] text-muted">
          {anomaly.features.map((f) => (
            <span key={f.name}>
              <span className="text-muted/70">{f.name}:</span> {f.detail}
            </span>
          ))}
        </div>
      )}

      <p className="mt-2 text-[11px] text-muted/70">
        Unsupervised robust-z outlier detection over approved history — sharpens as you approve more.
      </p>
    </div>
  );
}
