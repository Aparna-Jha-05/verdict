"use client";

import type { Extraction, ScalarKey } from "../../lib/types";
import { FIELD_LABELS, SCALAR_KEYS } from "../../lib/types";

const CONF_CLS: Record<string, string> = {
  high: "bg-green/15 text-green",
  medium: "bg-amber/15 text-amber",
  low: "bg-red/15 text-red",
};

export default function FieldReview({
  extraction,
  activeKey,
  onHover,
  onEdit,
}: {
  extraction: Extraction;
  activeKey: string | null;
  onHover: (key: string | null) => void;
  onEdit: (key: ScalarKey, value: string) => void;
}) {
  return (
    <div className="panel">
      <div className="panel-title">
        Extracted Fields
        <span className="font-normal normal-case tracking-normal text-muted">
          · overall {extraction.overall_confidence}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {SCALAR_KEYS.map((key) => {
          const f = extraction[key];
          const hl = activeKey === key;
          return (
            <div
              key={key}
              onMouseEnter={() => onHover(key)}
              onMouseLeave={() => onHover(null)}
              className={`rounded-xl border p-2.5 transition-all ${
                hl ? "border-gold bg-gold/[0.07]" : "border-line/20 bg-white/[0.02]"
              }`}
            >
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-wide text-muted">
                  {FIELD_LABELS[key as ScalarKey]}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${CONF_CLS[f.confidence]}`}>
                  {f.confidence}
                </span>
              </div>
              <input
                value={f.value}
                onChange={(e) => onEdit(key, e.target.value)}
                spellCheck={false}
                className="w-full rounded-lg border border-line/20 bg-inset/60 px-2.5 py-1.5 text-sm outline-none focus:border-violet"
              />
              {f.source && (
                <div className="mt-1.5 truncate text-[11px] italic text-muted" title={f.source}>
                  “{f.source}”
                </div>
              )}
            </div>
          );
        })}
      </div>

      {extraction.line_items.length > 0 && (
        <table className="mt-3.5 w-full border-collapse text-sm">
          <thead>
            <tr className="text-[11px] uppercase text-muted">
              <th className="border-b border-line/20 px-2 py-1.5 text-left font-medium">Description</th>
              <th className="border-b border-line/20 px-2 py-1.5 text-left font-medium">Qty</th>
              <th className="border-b border-line/20 px-2 py-1.5 text-left font-medium">Unit</th>
              <th className="border-b border-line/20 px-2 py-1.5 text-left font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {extraction.line_items.map((li, i) => (
              <tr
                key={i}
                onMouseEnter={() => onHover(`line_${i}`)}
                onMouseLeave={() => onHover(null)}
                className="hover:bg-gold/[0.05]"
              >
                <td className="border-b border-line/10 px-2 py-1.5">{li.description}</td>
                <td className="border-b border-line/10 px-2 py-1.5">{li.quantity}</td>
                <td className="border-b border-line/10 px-2 py-1.5">{li.unit_price.toFixed(2)}</td>
                <td className="border-b border-line/10 px-2 py-1.5">{li.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
