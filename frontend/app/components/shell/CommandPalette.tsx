"use client";

import {
  ClipboardList,
  FileText,
  LayoutDashboard,
  ScanLine,
  ScrollText,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useProcess } from "../../context/ProcessContext";
import { useTour } from "../../context/TourContext";

async function loadSample(name: string): Promise<File> {
  const res = await fetch(`/samples/${name}`);
  const blob = await res.blob();
  return new File([blob], name, { type: blob.type });
}

export default function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { processFile } = useProcess();
  const { start } = useTour();
  const [q, setQ] = useState("");

  const actions = useMemo(
    () => [
      { group: "Navigate", label: "Dashboard", icon: LayoutDashboard, run: () => router.push("/") },
      { group: "Navigate", label: "Review", icon: ScanLine, run: () => router.push("/review") },
      { group: "Navigate", label: "Ledger", icon: ScrollText, run: () => router.push("/ledger") },
      { group: "Navigate", label: "Audit", icon: ClipboardList, run: () => router.push("/audit") },
      { group: "Samples", label: "Process clean PDF", icon: FileText, run: async () => processFile(await loadSample("clean.pdf")) },
      { group: "Samples", label: "Process phone photo", icon: FileText, run: async () => processFile(await loadSample("photo_scan.jpg")) },
      { group: "Samples", label: "Process wrong-total invoice", icon: FileText, run: async () => processFile(await loadSample("wrong_total.pdf")) },
      { group: "Samples", label: "Process changed-bank invoice", icon: FileText, run: async () => processFile(await loadSample("changed_bank.pdf")) },
      { group: "Samples", label: "Process near-duplicate", icon: FileText, run: async () => processFile(await loadSample("near_duplicate.pdf")) },
      { group: "Help", label: "Start guided tour", icon: Sparkles, run: () => start() },
    ],
    [router, processFile, start]
  );

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(q.toLowerCase())
  );

  useEffect(() => {
    if (open) setQ("");
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[12vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-line/25 bg-surface shadow-2xl">
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search actions, samples, views…"
          className="w-full border-b border-line/15 bg-transparent px-4 py-3.5 text-sm outline-none placeholder:text-muted"
        />
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {filtered.length === 0 && (
            <p className="px-3 py-6 text-center text-sm text-muted">No matches.</p>
          )}
          {filtered.map((a, i) => {
            const Icon = a.icon;
            const first = i === 0 || filtered[i - 1].group !== a.group;
            return (
              <div key={a.label}>
                {first && (
                  <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-widest text-muted">
                    {a.group}
                  </p>
                )}
                <button
                  onClick={async () => {
                    onClose();
                    await a.run();
                  }}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm hover:bg-violet/10"
                >
                  <Icon className="h-4 w-4 text-muted" />
                  {a.label}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
