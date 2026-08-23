"use client";

import { Sparkles } from "lucide-react";
import type { Extraction } from "../../lib/types";

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
  onEdit: (key: string, value: string) => void;
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
        {extraction.fields.map((f) => {
          const hl = activeKey === f.key;
          return (
            <div
              key={f.key}
              onMouseEnter={() => onHover(f.key)}
              onMouseLeave={() => onHover(null)}
              className={`rounded-xl border p-2.5 transition-all ${
                hl ? "border-gold bg-gold/[0.07]" : "border-line/20 bg-white/[0.02]"
              }`}
            >
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="text-[11px] uppercase tracking-wide text-muted">{f.label}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${CONF_CLS[f.confidence]}`}>
                  {f.confidence}
                </span>
              </div>
              <input
                value={f.value}
                onChange={(e) => onEdit(f.key, e.target.value)}
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

      {extraction.tables.map((t) =>
        t.rows.length > 0 ? (
          <div key={t.name} className="mt-3.5">
            <div className="mb-1 text-[11px] uppercase tracking-wide text-muted">{t.label}</div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[420px] border-collapse text-sm">
                <thead>
                  <tr className="text-[11px] uppercase text-muted">
                    {t.columns.map((c) => (
                      <th key={c} className="border-b border-line/20 px-2 py-1.5 text-left font-medium">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {t.rows.map((r, i) => (
                    <tr
                      key={i}
                      onMouseEnter={() => onHover(`${t.name}_${i}`)}
                      onMouseLeave={() => onHover(null)}
                      className={activeKey === `${t.name}_${i}` ? "bg-gold/[0.07]" : "hover:bg-gold/[0.04]"}
                    >
                      {t.columns.map((c) => (
                        <td key={c} className="border-b border-line/10 px-2 py-1.5">
                          {r.cells[c]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null
      )}

      {extraction.additional_fields.length > 0 && (
        <div className="mt-4 rounded-xl border border-violet/25 bg-violet/[0.06] p-3">
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-violet">
            <Sparkles className="h-3.5 w-3.5" />
            Additional fields discovered
            <span className="font-normal normal-case tracking-normal text-muted">
              · not in the {extraction.domain} schema, captured anyway
            </span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {extraction.additional_fields.map((f, i) => (
              <div key={i} className="rounded-lg border border-line/15 bg-inset/40 px-2.5 py-1.5">
                <div className="text-[10px] uppercase tracking-wide text-muted">{f.label}</div>
                <div className="text-sm">{f.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
