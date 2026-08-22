"use client";

import { useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  processing: boolean;
}

// Sample files bundled under /public/samples for one-click demoing.
const SAMPLES: { label: string; file: string }[] = [
  { label: "Clean PDF", file: "clean.pdf" },
  { label: "Phone photo", file: "photo_scan.jpg" },
  { label: "Wrong total", file: "wrong_total.pdf" },
  { label: "Changed bank", file: "changed_bank.pdf" },
  { label: "Near-duplicate", file: "near_duplicate.pdf" },
];

export default function Uploader({ onFile, processing }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (files && files[0]) onFile(files[0]);
  };

  const loadSample = async (name: string) => {
    const res = await fetch(`/samples/${name}`);
    const blob = await res.blob();
    onFile(new File([blob], name, { type: blob.type }));
  };

  return (
    <div className="panel">
      <h2>Upload Invoice</h2>
      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <strong>Drop a PDF, PNG, or JPG</strong>
        <p>Scans and phone photos welcome — the model reads the image directly.</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/*"
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="samples">
        {SAMPLES.map((s) => (
          <button
            key={s.file}
            className="sample-chip"
            disabled={processing}
            onClick={() => loadSample(s.file)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {processing && (
        <div className="processing">
          <span className="spinner" />
          Reading the document, verifying, and checking for fraud…
        </div>
      )}
    </div>
  );
}
