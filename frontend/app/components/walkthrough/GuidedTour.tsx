"use client";

import { ArrowLeft, ArrowRight, Sparkles, X } from "lucide-react";
import { useProcess } from "../../context/ProcessContext";
import { TOUR_STEPS, useTour } from "../../context/TourContext";

async function loadSample(name: string): Promise<File> {
  const res = await fetch(`/samples/${name}`);
  const blob = await res.blob();
  return new File([blob], name, { type: blob.type });
}

export default function GuidedTour() {
  const { active, step, close, next, prev } = useTour();
  const { processFile } = useProcess();
  if (!active) return null;

  const s = TOUR_STEPS[step];
  const isLast = step === TOUR_STEPS.length - 1;

  const handleCta = async () => {
    if (s.sample) {
      // Load + process the sample; ProcessProvider navigates to /review.
      await processFile(await loadSample(s.sample));
    }
    if (isLast) close();
    else next();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center p-4 sm:items-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={close} />
      <div className="relative w-full max-w-md animate-pop rounded-2xl border border-line/25 bg-surface p-6 shadow-2xl">
        <button
          onClick={close}
          className="absolute right-3 top-3 rounded-lg p-1.5 text-muted hover:text-text"
          aria-label="Close tour"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="mb-3 flex items-center gap-2 text-gold">
          <Sparkles className="h-4 w-4" />
          <span className="text-[11px] font-semibold uppercase tracking-widest">
            Guided tour · {step + 1}/{TOUR_STEPS.length}
          </span>
        </div>

        <h2 className="text-lg font-bold">{s.title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>

        <div className="mt-5 flex items-center justify-between gap-3">
          <button
            onClick={prev}
            disabled={step === 0}
            className="btn btn-ghost px-3 py-2 text-xs disabled:opacity-40"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>
          <div className="flex gap-1.5">
            {TOUR_STEPS.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 rounded-full transition-all ${
                  i === step ? "w-5 bg-gold" : "w-1.5 bg-line/30"
                }`}
              />
            ))}
          </div>
          <button onClick={handleCta} className="btn btn-primary px-3 py-2 text-xs">
            {s.cta || (isLast ? "Done" : "Next")}
            {!isLast && <ArrowRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
