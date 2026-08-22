"use client";

import { Check, X } from "lucide-react";
import type { ValidationResult } from "../../lib/types";

export default function ValidationPanel({ validation }: { validation: ValidationResult }) {
  const failed = validation.checks.filter((c) => !c.passed).length;
  return (
    <div className="panel">
      <div className="panel-title">
        Validation
        <span className="font-normal normal-case tracking-normal text-muted">
          {failed === 0 ? "· all checks pass" : `· ${failed} failing`}
        </span>
      </div>
      <div className="space-y-1.5">
        {validation.checks.map((c) => (
          <div
            key={c.rule}
            className={`flex items-start gap-2.5 rounded-lg border p-2.5 ${
              c.passed ? "border-green/20 bg-green/10" : "border-red/35 bg-red/10"
            }`}
          >
            <span className={c.passed ? "text-green" : "text-red"}>
              {c.passed ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
            </span>
            <div>
              <div className="text-[13px] font-semibold">{c.rule}</div>
              <div className="mt-0.5 text-xs text-muted">{c.reason}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
