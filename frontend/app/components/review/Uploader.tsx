"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useProcess } from "../../context/ProcessContext";

const SAMPLE_JD =
  "We are hiring a Senior Data Scientist to build and deploy machine learning " +
  "systems in Python. Requirements: strong experience with PyTorch or TensorFlow, " +
  "NLP and large language models, SQL, and production MLOps on AWS with Docker. " +
  "You will lead model development and ship models to production at scale.";

type Sample = { label: string; file: string; domain?: string; jd?: string };

const SAMPLES: Sample[] = [
  { label: "Clean invoice", file: "clean.pdf", domain: "invoice" },
  { label: "Phone photo", file: "photo_scan.jpg", domain: "invoice" },
  { label: "Wrong total", file: "wrong_total.pdf", domain: "invoice" },
  { label: "Changed bank", file: "changed_bank.pdf", domain: "invoice" },
  { label: "Near-duplicate", file: "near_duplicate.pdf", domain: "invoice" },
  { label: "Résumé ↔ JD", file: "resume.pdf", domain: "resume", jd: SAMPLE_JD },
  { label: "Receipt", file: "receipt.pdf", domain: "receipt" },
];

async function loadSample(name: string): Promise<File> {
  const res = await fetch(`/samples/${name}`);
  const blob = await res.blob();
  return new File([blob], name, { type: blob.type });
}

export default function Uploader({ navigate = false }: { navigate?: boolean }) {
  const {
    processFile,
    processing,
    domains,
    selectedDomain,
    setSelectedDomain,
    secondInput,
    setSecondInput,
  } = useProcess();
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const active = domains.find((d) => d.name === selectedDomain);
  const needsSecond = active?.needs_second_input;

  return (
    <div className="panel">
      <div className="panel-title">Upload Document</div>

      <div className="mb-3">
        <label className="mb-1 block text-[11px] uppercase tracking-wide text-muted">
          Document type
        </label>
        <select
          value={selectedDomain}
          onChange={(e) => setSelectedDomain(e.target.value)}
          className="w-full rounded-lg border border-line/20 bg-inset/60 px-2.5 py-2 text-sm outline-none focus:border-violet"
        >
          <option value="auto">✨ Auto-detect</option>
          {domains.map((d) => (
            <option key={d.name} value={d.name}>
              {d.label}
            </option>
          ))}
        </select>
      </div>

      {needsSecond && (
        <div className="mb-3">
          <label className="mb-1 block text-[11px] uppercase tracking-wide text-muted">
            {active?.second_input_label} (paste text to match against)
          </label>
          <textarea
            value={secondInput}
            onChange={(e) => setSecondInput(e.target.value)}
            rows={3}
            placeholder={`Paste the ${active?.second_input_label.toLowerCase()} here…`}
            className="w-full resize-y rounded-lg border border-line/20 bg-inset/60 px-2.5 py-2 text-sm outline-none focus:border-violet"
          />
        </div>
      )}

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          if (e.dataTransfer.files[0]) processFile(e.dataTransfer.files[0], navigate);
        }}
        className={`cursor-pointer rounded-xl border-[1.5px] border-dashed p-7 text-center transition-all ${
          drag ? "border-gold bg-gold/[0.06]" : "border-line/40 bg-violet/[0.04] hover:border-gold"
        }`}
      >
        <UploadCloud className="mx-auto mb-2 h-7 w-7 text-violet" />
        <strong className="text-text">Drop a PDF, PNG, or JPG</strong>
        <p className="mt-1 text-[13px] text-muted">
          Scans and phone photos welcome — the model reads the image directly.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/*"
          hidden
          onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0], navigate)}
        />
      </div>

      <div className="mt-3">
        <div className="mb-1.5 text-[10px] uppercase tracking-wide text-muted">
          Demo samples
        </div>
        <div className="flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s.file}
              disabled={processing}
              onClick={async () =>
                processFile(await loadSample(s.file), navigate, {
                  domain: s.domain,
                  secondInput: s.jd,
                })
              }
              className="chip"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {processing && (
        <div className="mt-3 flex items-center gap-3 text-sm text-violet">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet/30 border-t-gold" />
          Reading the document, verifying, and checking integrity…
        </div>
      )}
    </div>
  );
}
