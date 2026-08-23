"use client";

import { Activity, FileText, ScanLine, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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

type TabId = "fields" | "checks" | "integrity" | "signals";

export default function ReviewPage() {
  const { resp, extraction, error, processing, activeKey, setActiveKey, editField } =
    useProcess();
  const [tab, setTab] = useState<TabId>("fields");
  const [visited, setVisited] = useState<Set<TabId>>(new Set(["fields"]));

  const hasSignals = !!(resp?.similarity || resp?.anomaly);

  // Counts for the tab badges.
  const failCount = resp?.validation.checks.filter((c) => !c.passed).length ?? 0;
  const flagCount = useMemo(() => {
    const flags = (resp?.integrity as any)?.flags ?? [];
    return flags.filter((f: any) => f.severity && f.severity !== "info").length;
  }, [resp]);

  // Reset when a new document is processed.
  useEffect(() => {
    if (!resp) return;
    setTab("fields");
    setVisited(new Set(["fields"]));
  }, [resp]);

  const go = (id: TabId) => {
    setTab(id);
    setVisited((v) => new Set(v).add(id));
  };

  const reviewed = visited.has("checks") && visited.has("integrity");

  const TABS: { id: TabId; label: string; icon: typeof FileText; badge?: number; tone?: string }[] = [
    { id: "fields", label: "Fields", icon: FileText },
    { id: "checks", label: "Checks", icon: ShieldCheck, badge: failCount, tone: failCount ? "red" : "green" },
    { id: "integrity", label: "Integrity", icon: ScanLine, badge: flagCount, tone: flagCount ? "red" : "green" },
    ...(hasSignals ? [{ id: "signals" as TabId, label: "Signals", icon: Activity, tone: "violet" }] : []),
  ];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.05fr_1fr]">
      <div className="flex flex-col gap-5">
        <Uploader />
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

      <div className="flex flex-col gap-4">
        {error && (
          <div className="rounded-xl border border-red/50 bg-red/10 px-4 py-3 text-sm text-red">
            {error}
            {/credits/i.test(error) && (
              <a href="/billing" className="ml-2 font-semibold underline">
                Go to Billing →
              </a>
            )}
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
            {/* Segmented tab bar */}
            <div className="flex gap-1 rounded-xl border border-line/20 bg-inset/50 p-1">
              {TABS.map((t) => {
                const Icon = t.icon;
                const active = tab === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => go(t.id)}
                    className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold transition-colors ${
                      active ? "bg-violet/20 text-text shadow-sm" : "text-muted hover:text-text"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {t.label}
                    {t.badge !== undefined && t.badge > 0 && (
                      <span className={`rounded-full px-1.5 text-[10px] ${
                        t.tone === "red" ? "bg-red/20 text-red" : "bg-green/20 text-green"
                      }`}>
                        {t.badge}
                      </span>
                    )}
                    {t.id === "integrity" && t.badge === 0 && (
                      <span className="rounded-full bg-green/20 px-1.5 text-[10px] text-green">✓</span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Tab body */}
            {tab === "fields" && (
              <FieldReview
                extraction={extraction}
                activeKey={activeKey}
                onHover={setActiveKey}
                onEdit={editField}
              />
            )}
            {tab === "checks" && <ValidationPanel validation={resp.validation} />}
            {tab === "integrity" && (
              <IntegrityPanel
                integrity={resp.integrity}
                label={resp.integrity_label}
                domain={resp.domain}
                extraction={extraction}
              />
            )}
            {tab === "signals" && (
              <div className="flex flex-col gap-4">
                {resp.similarity && <SimilarityPanel similarity={resp.similarity} />}
                {resp.anomaly && <AnomalyPanel anomaly={resp.anomaly} />}
                {!resp.similarity && !resp.anomaly && (
                  <div className="panel text-sm text-muted">No ML signals for this document.</div>
                )}
              </div>
            )}

            <ApproveBar reviewed={reviewed} />
            {!reviewed && (
              <p className="-mt-1 text-center text-[11px] text-muted">
                Open the <b>Checks</b> and <b>Integrity</b> tabs to enable approval.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
