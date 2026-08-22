"use client";

import type { ValidationResult } from "../lib/types";

export default function ValidationPanel({
  validation,
}: {
  validation: ValidationResult;
}) {
  const failed = validation.checks.filter((c) => !c.passed).length;
  return (
    <div className="panel">
      <h2>
        Validation{" "}
        <span className="count">
          {failed === 0
            ? "· all checks pass"
            : `· ${failed} failing`}
        </span>
      </h2>
      {validation.checks.map((c) => (
        <div key={c.rule} className={`check-row ${c.passed ? "pass" : "fail"}`}>
          <span className="check-icon">{c.passed ? "✓" : "✕"}</span>
          <div className="check-body">
            <div className="rule">{c.rule}</div>
            <div className="reason">{c.reason}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
