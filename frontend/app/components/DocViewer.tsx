"use client";

import type { BBox, Extraction, ScalarKey } from "../lib/types";
import { FIELD_LABELS, SCALAR_KEYS } from "../lib/types";

interface Props {
  imageB64: string;
  extraction: Extraction;
  activeKey: string | null;
  onHover: (key: string | null) => void;
}

function validBox(b: BBox | undefined): boolean {
  if (!b || b.length !== 4) return false;
  const [x0, y0, x1, y1] = b;
  return x1 > x0 && y1 > y0 && x1 <= 1.001 && y1 <= 1.001 && x0 >= -0.001;
}

function style(b: BBox): React.CSSProperties {
  const [x0, y0, x1, y1] = b;
  return {
    left: `${x0 * 100}%`,
    top: `${y0 * 100}%`,
    width: `${(x1 - x0) * 100}%`,
    height: `${(y1 - y0) * 100}%`,
  };
}

export default function DocViewer({
  imageB64,
  extraction,
  activeKey,
  onHover,
}: Props) {
  const boxes: { key: string; label: string; bbox: BBox }[] = [];

  for (const key of SCALAR_KEYS) {
    const f = extraction[key];
    if (f && validBox(f.bbox)) {
      boxes.push({ key, label: FIELD_LABELS[key as ScalarKey], bbox: f.bbox });
    }
  }
  extraction.line_items.forEach((li, i) => {
    if (validBox(li.bbox)) {
      boxes.push({
        key: `line_${i}`,
        label: li.description || `Line ${i + 1}`,
        bbox: li.bbox,
      });
    }
  });

  return (
    <div className="panel">
      <h2>
        Source Document{" "}
        <span className="count">
          {boxes.length > 0
            ? `· ${boxes.length} field boxes`
            : "· boxes unavailable, see field sources"}
        </span>
      </h2>
      <div className="doc-wrap">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`data:image/png;base64,${imageB64}`} alt="Invoice page" />
        {boxes.map((b) => {
          const active = activeKey === b.key;
          return (
            <div
              key={b.key}
              className={`bbox ${active ? "active" : ""}`}
              style={style(b.bbox)}
              onMouseEnter={() => onHover(b.key)}
              onMouseLeave={() => onHover(null)}
            >
              {active && <span className="bbox-label">{b.label}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
