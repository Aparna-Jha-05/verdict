"use client";

import { ScanLine } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import AnomalyPanel from "../components/review/AnomalyPanel";
import ApproveBar from "../components/review/ApproveBar";
import BadgeBar from "../components/review/BadgeBar";
import DocViewer from "../components/review/DocViewer";
import FieldReview from "../components/review/FieldReview";
import IntegrityPanel from "../components/review/IntegrityPanel";
import SimilarityPanel from "../components/review/SimilarityPanel";
import Uploader from "../components/review/Uploader";
import ValidationPanel from "../components/review/ValidationPanel";
import { useProcess } from "../context/ProcessContext";

export default function ReviewPage() {
  const { resp, extraction, error, processing, activeKey, setActiveKey, editField } =
    useProcess();
  const [reviewed, setReviewed] = useState(false);
  const gateRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!resp) return;
    setReviewed(false);
    const node = gateRef.current;
    if (!node) return;
    const io = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && setReviewed(true),
      { threshold: 0.4 }
    );
    io.observe(node);
    return () => io.disconnect();
  }, [resp]);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.05fr_1fr]">
      <div className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <Uploader />
          </div>
        </div>
        {resp && extraction && (
          <>
            <BadgeBar resp={resp} />
            <DocViewer
              imageB64={resp.page_image_b64}
              extraction={extraction}
              activeKey={activeKey}
              onHover={setActiveKey}
            />
          </>
        )}
      </div>

      <div className="flex flex-col gap-5">
        {error && (
          <div className="rounded-xl border border-red/50 bg-red/10 px-4 py-3 text-sm text-red">
            {error}
          </div>
        )}

        {!resp && !error && (
          <div className="panel">
            <div className="flex flex-col items-center gap-3 py-14 text-center text-muted">
              <ScanLine className="h-8 w-8 text-violet/60" />
              <p className="max-w-xs text-sm">
                {processing
                  ? "Processing your document…"
                  : "Pick a document type (or Auto-detect), upload a file, and see extraction, validation, and integrity checks — each field boxed on the document."}
              </p>
            </div>
          </div>
        )}

        {resp && extraction && (
          <>
            <FieldReview
              extraction={extraction}
              activeKey={activeKey}
              onHover={setActiveKey}
              onEdit={editField}
            />
            {resp.similarity && <SimilarityPanel similarity={resp.similarity} />}
            {resp.anomaly && <AnomalyPanel anomaly={resp.anomaly} />}
            <ValidationPanel validation={resp.validation} />
            <div ref={gateRef}>
              <IntegrityPanel
                integrity={resp.integrity}
                label={resp.integrity_label}
                domain={resp.domain}
                extraction={extraction}
              />
            </div>
            <ApproveBar reviewed={reviewed} />
          </>
        )}
      </div>
    </div>
  );
}
