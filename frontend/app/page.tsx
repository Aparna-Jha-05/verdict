"use client";

import { Sparkles } from "lucide-react";
import DomainGallery from "./components/dashboard/DomainGallery";
import RecentActivity from "./components/dashboard/RecentActivity";
import SummaryRow from "./components/dashboard/SummaryRow";
import Uploader from "./components/review/Uploader";
import { useTour } from "./context/TourContext";

export default function DashboardPage() {
  const { start } = useTour();

  return (
    <div className="space-y-5">
      <div className="panel flex flex-col items-start justify-between gap-4 bg-gradient-to-br from-violet/[0.12] to-transparent sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-extrabold tracking-tight">
            One engine for every document. Read · verify · catch · approve.
          </h2>
          <p className="mt-1 text-sm text-muted">
            A vision model reads any document; deterministic rules and a human decide.
            Invoices, receipts, résumés, IDs, contracts and more — new domains added over time.
          </p>
        </div>
        <button onClick={start} className="btn btn-primary shrink-0">
          <Sparkles className="h-4 w-4" /> Guided tour
        </button>
      </div>

      <SummaryRow />
      <DomainGallery />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1fr]">
        <Uploader navigate />
        <RecentActivity />
      </div>
    </div>
  );
}
