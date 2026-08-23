"use client";

import type { BBox, Extraction } from "../../lib/types";

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
}: {
  imageB64: string;
  extraction: Extraction;
  activeKey: string | null;
  onHover: (key: string | null) => void;
}) {
  const boxes: { key: string; label: string; bbox: BBox }[] = [];
  for (const f of extraction.fields) {
    if (validBox(f.bbox)) boxes.push({ key: f.key, label: f.label, bbox: f.bbox });
  }
  extraction.tables.forEach((t) => {
    t.rows.forEach((r, i) => {
      if (validBox(r.bbox)) {
        const first = t.columns[0];
        boxes.push({
          key: `${t.name}_${i}`,
          label: r.cells[first] || `${t.label} ${i + 1}`,
          bbox: r.bbox,
        });
      }
    });
  });

  return (
    <div className="panel">
      <div className="panel-title">
        Source Document
        <span className="font-normal normal-case tracking-normal text-muted">
          {boxes.length > 0
            ? `· ${boxes.length} field boxes`
            : "· boxes unavailable — see field sources"}
        </span>
      </div>
      <div className="relative overflow-hidden rounded-xl bg-black leading-none">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`data:image/png;base64,${imageB64}`} alt="Document page" className="block w-full" />
        {boxes.map((b) => {
          const active = activeKey === b.key;
          return (
            <div
              key={b.key}
              onMouseEnter={() => onHover(b.key)}
              onMouseLeave={() => onHover(null)}
              className={`absolute cursor-pointer rounded-[3px] border-2 transition-all ${
                active
                  ? "border-gold bg-gold/25 shadow-[0_0_0_2px_rgba(245,196,81,0.35),0_0_18px_rgba(245,196,81,0.4)]"
                  : "border-violet/50 bg-violet/10"
              }`}
              style={style(b.bbox)}
            >
              {active && (
                <span className="pointer-events-none absolute -top-[18px] left-[-2px] whitespace-nowrap rounded-[3px] bg-gold px-1.5 py-px text-[10px] font-semibold leading-tight text-on-accent">
                  {b.label}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
