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

          {similarity.coverage !== null && (
            <div className="mt-3 border-t border-line/15 pt-3">
              <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide text-muted">
                <span>Skill coverage</span>
                <span className="font-mono text-text">{Math.round(similarity.coverage * 100)}% of role skills</span>
              </div>
              {similarity.matched.length > 0 && (
                <div className="mb-1.5 flex flex-wrap gap-1.5">
                  {similarity.matched.map((s) => (
                    <span key={s} className="rounded-md bg-green/15 px-2 py-0.5 text-[11px] capitalize text-green">
                      ✓ {s}
                    </span>
                  ))}
                </div>
              )}
              {similarity.missing.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {similarity.missing.map((s) => (
                    <span key={s} className="rounded-md bg-red/12 px-2 py-0.5 text-[11px] capitalize text-red">
                      ✕ {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          <p className="mt-2 text-[11px] text-muted/70">
            Semantic + skill-level matching (embeddings) — a signal for the recruiter, not an auto-decision.
          </p>
        </>
      )}
    </div>
  );
}
