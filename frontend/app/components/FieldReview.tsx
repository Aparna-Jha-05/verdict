"use client";

import type { Extraction, ScalarKey } from "../lib/types";
import { FIELD_LABELS, SCALAR_KEYS } from "../lib/types";

interface Props {
  extraction: Extraction;
  activeKey: string | null;
  onHover: (key: string | null) => void;
  onEdit: (key: ScalarKey, value: string) => void;
}

export default function FieldReview({
  extraction,
  activeKey,
  onHover,
  onEdit,
}: Props) {
  return (
    <div className="panel">
      <h2>
        Extracted Fields{" "}
        <span className="count">· overall {extraction.overall_confidence}</span>
      </h2>
      <div className="field-grid">
        {SCALAR_KEYS.map((key) => {
          const f = extraction[key];
          const hl = activeKey === key;
          return (
            <div
              key={key}
              className={`field-card ${hl ? "hl" : ""}`}
              onMouseEnter={() => onHover(key)}
              onMouseLeave={() => onHover(null)}
              title={f.source ? `Source: ${f.source}` : undefined}
            >
              <label>
                {FIELD_LABELS[key as ScalarKey]}
                <span className={`conf ${f.confidence}`}>{f.confidence}</span>
              </label>
              <input
                value={f.value}
                onChange={(e) => onEdit(key, e.target.value)}
                spellCheck={false}
              />
              {f.source && <div className="field-source">“{f.source}”</div>}
            </div>
          );
        })}
      </div>

      {extraction.line_items.length > 0 && (
        <table className="line-items">
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {extraction.line_items.map((li, i) => (
              <tr
                key={i}
                onMouseEnter={() => onHover(`line_${i}`)}
                onMouseLeave={() => onHover(null)}
              >
                <td>{li.description}</td>
                <td>{li.quantity}</td>
                <td>{li.unit_price.toFixed(2)}</td>
                <td>{li.amount.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
