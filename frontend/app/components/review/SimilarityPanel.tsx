"use client";

import { GitCompareArrows } from "lucide-react";
import type { SimilarityResult } from "../../lib/types";

const BAND: Record<string, string> = {
  "Strong match": "text-green",
  "Moderate match": "text-amber",
  "Weak match": "text-red",
  unavailable: "text-muted",
};

export default function SimilarityPanel({ similarity }: { similarity: SimilarityResult }) {
  const pct = Math.round(similarity.score * 100);
  const tint = BAND[similarity.verdict] || "text-violet";
  const barColor =
    similarity.verdict === "Strong match"
      ? "bg-green"
      : similarity.verdict === "Moderate match"
      ? "bg-amber"
      : "bg-red";

  return (
    <div className="panel">
      <div className="panel-title">
        <GitCompareArrows className="h-4 w-4 text-violet" />
        {similarity.label}
      </div>
      {similarity.verdict === "unavailable" ? (
        <p className="text-[13px] text-muted">{similarity.detail}</p>
      ) : (
        <>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-3xl font-extrabold tabular-nums">{pct}%</span>
            <span className={`text-sm font-semibold ${tint}`}>{similarity.verdict}</span>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-inset">
            <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-2 text-xs text-muted">{similarity.detail}</p>
          <p className="mt-1 text-[11px] text-muted/70">
            Deterministic cosine over local embeddings — the model never scores the match.
          </p>
        </>
      )}
    </div>
  );
}
