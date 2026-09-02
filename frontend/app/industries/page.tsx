"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import DomainIcon from "../components/shell/DomainIcon";
import { getIndustries } from "../lib/api";
import type { Industry } from "../lib/types";

export default function IndustriesPage() {
  const router = useRouter();
  const [industries, setIndustries] = useState<Industry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIndustries()
      .then(setIndustries)
      .catch(() => setIndustries([]))
      .finally(() => setLoading(false));
  }, []);

  const go = (key: string) => router.push(`/review?industry=${key}`);

  return (
    <div className="space-y-5">
      <div className="panel bg-gradient-to-br from-violet/[0.12] to-transparent">
        <h2 className="text-xl font-extrabold tracking-tight">Choose your workspace</h2>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          Credence is one engine across every industry. Pick a workspace to scope it to just
          your document types — or jump straight in and let auto-detect decide.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <label className="text-[11px] uppercase tracking-wide text-muted">Quick jump</label>
          <select
            defaultValue=""
            onChange={(e) => e.target.value && go(e.target.value)}
            className="rounded-lg border border-line/20 bg-inset/60 px-2.5 py-2 text-sm outline-none focus:border-violet"
          >
            <option value="" disabled>Select an industry…</option>
            {industries.map((i) => (
              <option key={i.key} value={i.key}>{i.label}</option>
            ))}
          </select>
          <button onClick={() => router.push("/review")} className="btn btn-ghost text-sm">
            Skip · auto-detect any document
          </button>
        </div>
      </div>

      {loading ? (
        <div className="panel py-16 text-center text-muted">Loading industries…</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {industries.map((ind) => (
            <button
              key={ind.key}
              onClick={() => go(ind.key)}
              className="group panel text-left transition-all hover:-translate-y-0.5 hover:border-gold/40"
            >
              <div className="mb-3 flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-violet/20 to-gold/20 text-violet">
                  <DomainIcon name={ind.icon} className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <div className="font-bold leading-tight">{ind.label}</div>
                  <div className="text-[11px] text-muted">{ind.count} document type{ind.count > 1 ? "s" : ""}</div>
                </div>
                <ArrowRight className="ml-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-gold" />
              </div>
              <p className="text-[13px] text-muted">{ind.tagline}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {ind.documents.slice(0, 5).map((d) => (
                  <span key={d.name} className="rounded-md border border-line/15 bg-white/[0.03] px-2 py-0.5 text-[11px] text-muted">
                    {d.label}
                  </span>
                ))}
                {ind.documents.length > 5 && (
                  <span className="px-1 text-[11px] text-muted">+{ind.documents.length - 5}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
