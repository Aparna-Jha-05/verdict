"use client";

import { useEffect, useRef, useState } from "react";
import ApproveBar from "./components/ApproveBar";
import DocViewer from "./components/DocViewer";
import FieldReview from "./components/FieldReview";
import FraudPanel from "./components/FraudPanel";
import Uploader from "./components/Uploader";
import ValidationPanel from "./components/ValidationPanel";
import { processInvoice } from "./lib/api";
import type { Extraction, ProcessResponse, ScalarKey } from "./lib/types";

export default function Home() {
  const [processing, setProcessing] = useState(false);
  const [resp, setResp] = useState<ProcessResponse | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fraudRef = useRef<HTMLDivElement>(null);

  const onFile = async (file: File) => {
    setProcessing(true);
    setError(null);
    setResp(null);
    setExtraction(null);
    setReviewed(false);
    setActiveKey(null);
    try {
      const r = await processInvoice(file);
      setResp(r);
      setExtraction(r.extraction);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setProcessing(false);
    }
  };

  const editField = (key: ScalarKey, value: string) => {
    setExtraction((prev) =>
      prev ? { ...prev, [key]: { ...prev[key], value } } : prev
    );
  };

  // Gate approval on the human having scrolled the fraud panel into view.
  useEffect(() => {
    if (!resp) return;
    const node = fraudRef.current;
    if (!node) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setReviewed(true);
      },
      { threshold: 0.4 }
    );
    io.observe(node);
    return () => io.disconnect();
  }, [resp]);

  return (
    <main className="shell">
      <header className="app-header">
        <div>
          <h1 className="app-title">Verdict</h1>
          <p className="app-subtitle">
            Vision-first extraction · deterministic verification · human approval gate
          </p>
        </div>
        {resp && (
          <div className="badges">
            <span className="badge model">model: {resp.model_used}</span>
            <span className="badge">source: {resp.source_type}</span>
            {resp.escalated && (
              <span className="badge escalated">⚡ escalated</span>
            )}
          </div>
        )}
      </header>

      <div className="grid">
        <div className="col">
          <Uploader onFile={onFile} processing={processing} />
          {resp && extraction && (
            <DocViewer
              imageB64={resp.page_image_b64}
              extraction={extraction}
              activeKey={activeKey}
              onHover={setActiveKey}
            />
          )}
        </div>

        <div className="col">
          {error && <div className="error-banner">{error}</div>}

          {!resp && !error && !processing && (
            <div className="panel">
              <div className="empty-hint">
                Upload an invoice or pick a sample to see extraction, validation,
                and fraud checks — with every field boxed on the document.
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
              <ValidationPanel validation={resp.validation} />
              <div ref={fraudRef}>
                <FraudPanel fraud={resp.fraud} />
              </div>
              <ApproveBar
                extraction={extraction}
                reviewed={reviewed}
                onApproved={() => undefined}
              />
            </>
          )}
        </div>
      </div>
    </main>
  );
}
