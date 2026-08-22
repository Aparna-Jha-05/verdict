"use client";

import { useEffect, useState } from "react";
import { API_BASE, getHealth } from "../../lib/api";

type Status = "checking" | "online" | "waking" | "offline";

export default function ConnectionFooter() {
  const [status, setStatus] = useState<Status>("checking");
  const [latency, setLatency] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      const started = performance.now();
      // If the first ping is slow, the free-tier backend is likely waking.
      const slowTimer = setTimeout(() => {
        if (mounted) setStatus((s) => (s === "online" ? s : "waking"));
      }, 1500);
      const ok = await getHealth();
      clearTimeout(slowTimer);
      if (!mounted) return;
      setLatency(Math.round(performance.now() - started));
      setStatus(ok ? "online" : "offline");
    };
    check();
    const id = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const map: Record<Status, { color: string; label: string }> = {
    checking: { color: "bg-amber", label: "Checking backend…" },
    online: { color: "bg-green", label: "Backend online" },
    waking: { color: "bg-amber animate-pulse", label: "Waking backend (free tier)…" },
    offline: { color: "bg-red", label: "Backend unreachable" },
  };
  const s = map[status];
  const host = API_BASE.replace(/^https?:\/\//, "");

  return (
    <footer className="flex items-center justify-between gap-3 border-t border-line/15 px-4 py-2.5 text-[11px] text-muted md:px-8">
      <div className="flex items-center gap-2">
        <span className={`dot ${s.color}`} />
        <span>{s.label}</span>
        {status === "online" && latency !== null && (
          <span className="text-muted/60">· {latency} ms</span>
        )}
      </div>
      <span className="hidden truncate font-mono text-muted/60 sm:block">{host}</span>
    </footer>
  );
}
