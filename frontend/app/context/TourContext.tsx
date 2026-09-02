"use client";

import { createContext, useContext, useState } from "react";

export interface TourStep {
  title: string;
  body: string;
  sample?: string; // filename under /public/samples to auto-load
  cta?: string;
}

export const TOUR_STEPS: TourStep[] = [
  {
    title: "Welcome to Credence",
    body: "Credence reads any invoice with a vision model, verifies it with deterministic rules that never call an LLM, catches fraud a human would miss, and keeps the final call with you. This 90-second tour walks the whole arc.",
    cta: "Start the tour",
  },
  {
    title: "1 · It shows its work",
    body: "A clean PDF: fields populate with confidence badges, and every value is boxed on the document itself. Hover a field to light up its source box.",
    sample: "clean.pdf",
    cta: "Load the clean invoice",
  },
  {
    title: "2 · Vision-first + escalation",
    body: "A skewed phone photo. Low confidence auto-escalates to a stronger model — watch the ⚡ escalated badge — then it extracts correctly. Route by confidence, not brute force.",
    sample: "photo_scan.jpg",
    cta: "Load the phone photo",
  },
  {
    title: "3 · The deterministic catch",
    body: "This invoice's total doesn't add up. Extraction succeeds — the model believed the document — but the validation layer throws a loud red flag with the exact reason.",
    sample: "wrong_total.pdf",
    cta: "Load the wrong-total invoice",
  },
  {
    title: "4 · Real fraud, caught",
    body: "A known vendor's bank account has changed versus their history. The fraud layer flags it — the single most common real-world AP fraud — and you can draft a vendor verification query in one click.",
    sample: "changed_bank.pdf",
    cta: "Load the changed-bank invoice",
  },
  {
    title: "5 · Approve, log, self-defend",
    body: "Approve a clean invoice: a mock payment action fires, a CSV downloads, and it's written to the ledger — where it now blocks future duplicates. Check the Ledger and Audit views to see the trail.",
    cta: "Finish tour",
  },
];

interface TourState {
  active: boolean;
  step: number;
  start: () => void;
  close: () => void;
  next: () => void;
  prev: () => void;
}

const Ctx = createContext<TourState | null>(null);

export function TourProvider({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);

  return (
    <Ctx.Provider
      value={{
        active,
        step,
        start: () => {
          setStep(0);
          setActive(true);
        },
        close: () => setActive(false),
        next: () => setStep((s) => Math.min(s + 1, TOUR_STEPS.length - 1)),
        prev: () => setStep((s) => Math.max(s - 1, 0)),
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useTour() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTour must be used within TourProvider");
  return ctx;
}
