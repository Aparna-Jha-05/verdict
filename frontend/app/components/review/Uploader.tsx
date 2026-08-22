"use client";

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useProcess } from "../../context/ProcessContext";

const SAMPLES: { label: string; file: string }[] = [
  { label: "Clean PDF", file: "clean.pdf" },
  { label: "Phone photo", file: "photo_scan.jpg" },
  { label: "Wrong total", file: "wrong_total.pdf" },
  { label: "Changed bank", file: "changed_bank.pdf" },
  { label: "Near-duplicate", file: "near_duplicate.pdf" },
];

async function loadSample(name: string): Promise<File> {
  const res = await fetch(`/samples/${name}`);
  const blob = await res.blob();
  return new File([blob], name, { type: blob.type });
}

export default function Uploader({ navigate = false }: { navigate?: boolean }) {
  const { processFile, processing } = useProcess();
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  return (
    <div className="panel">
      <div className="panel-title">Upload Invoice</div>
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
        className={`cursor-pointer rounded-xl border-[1.5px] border-dashed p-8 text-center transition-all ${
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

      <div className="mt-3 flex flex-wrap gap-2">
        {SAMPLES.map((s) => (
          <button
            key={s.file}
            disabled={processing}
            onClick={async () => processFile(await loadSample(s.file), navigate)}
            className="chip"
          >
            {s.label}
          </button>
        ))}
      </div>

      {processing && (
        <div className="mt-3 flex items-center gap-3 text-sm text-violet">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-violet/30 border-t-gold" />
          Reading the document, verifying, and checking for fraud…
        </div>
      )}
    </div>
  );
}
