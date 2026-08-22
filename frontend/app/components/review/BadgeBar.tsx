"use client";

import { Zap } from "lucide-react";
import type { ProcessResponse } from "../../lib/types";

export default function BadgeBar({ resp }: { resp: ProcessResponse }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="badge border-line/40 text-violet">model: {resp.model_used}</span>
      <span className="badge">source: {resp.source_type}</span>
      {resp.escalated && (
        <span className="badge animate-pop border-gold/50 bg-gold/10 text-gold">
          <Zap className="mr-1 inline h-3 w-3" />
          escalated
        </span>
      )}
    </div>
  );
}
