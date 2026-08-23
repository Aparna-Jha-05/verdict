"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  approveDocument,
  getDomains,
  processDocument,
} from "../lib/api";
import type {
  ApproveResponse,
  DomainInfo,
  Extraction,
  ProcessResponse,
} from "../lib/types";
import { useAuth } from "./AuthContext";

interface ProcessState {
  domains: DomainInfo[];
  selectedDomain: string; // "auto" or a pack name
  setSelectedDomain: (d: string) => void;
  secondInput: string;
  setSecondInput: (s: string) => void;

  fileName: string | null;
  processing: boolean;
  resp: ProcessResponse | null;
  extraction: Extraction | null;
  error: string | null;
  approved: ApproveResponse | null;
  activeKey: string | null;

  processFile: (
    file: File,
    navigate?: boolean,
    opts?: { domain?: string; secondInput?: string }
  ) => Promise<void>;
  editField: (key: string, value: string) => void;
  approve: () => Promise<void>;
  setActiveKey: (k: string | null) => void;
  reset: () => void;
  bump: number;
}

const Ctx = createContext<ProcessState | null>(null);

export function ProcessProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { refreshBilling } = useAuth();
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [selectedDomain, setSelectedDomain] = useState("auto");
  const [secondInput, setSecondInput] = useState("");

  const [fileName, setFileName] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [resp, setResp] = useState<ProcessResponse | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approved, setApproved] = useState<ApproveResponse | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  // Retry domains until it lands — the free-tier backend may be asleep or the
  // network may blip on first load, and an empty domain list breaks the app.
  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const load = async () => {
      while (!cancelled && attempts < 20) {
        attempts += 1;
        try {
          const d = await getDomains();
          if (d.length && !cancelled) {
            setDomains(d);
            return;
          }
        } catch {
          /* retry */
        }
        await new Promise((r) => setTimeout(r, Math.min(2000 + attempts * 500, 6000)));
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const processFile = useCallback(
    async (
      file: File,
      navigate = true,
      opts?: { domain?: string; secondInput?: string }
    ) => {
      const domain = opts?.domain ?? selectedDomain;
      const second = opts?.secondInput ?? secondInput;
      if (opts?.domain) setSelectedDomain(opts.domain);
      if (opts?.secondInput !== undefined) setSecondInput(opts.secondInput);
      setProcessing(true);
      setError(null);
      setResp(null);
      setExtraction(null);
      setApproved(null);
      setActiveKey(null);
      setFileName(file.name);
      if (navigate) router.push("/review");
      try {
        const r = await processDocument(file, domain, second);
        setResp(r);
        setExtraction(r.extraction);
        setBump((b) => b + 1);
        refreshBilling();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong.");
      } finally {
        setProcessing(false);
      }
    },
    [router, selectedDomain, secondInput, refreshBilling]
  );

  const editField = useCallback((key: string, value: string) => {
    setExtraction((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        fields: prev.fields.map((f) => (f.key === key ? { ...f, value } : f)),
      };
    });
  }, []);

  const approve = useCallback(async () => {
    if (!extraction || !resp) return;
    const action =
      resp.domain === "invoice"
        ? "queued for payment"
        : resp.domain === "resume"
        ? "shortlisted"
        : "approved & logged";
    const r = await approveDocument(resp.domain, extraction, action);
    setApproved(r);
    setBump((b) => b + 1);
  }, [extraction, resp]);

  const reset = useCallback(() => {
    setResp(null);
    setExtraction(null);
    setApproved(null);
    setError(null);
    setActiveKey(null);
    setFileName(null);
  }, []);

  return (
    <Ctx.Provider
      value={{
        domains,
        selectedDomain,
        setSelectedDomain,
        secondInput,
        setSecondInput,
        fileName,
        processing,
        resp,
        extraction,
        error,
        approved,
        activeKey,
        processFile,
        editField,
        approve,
        setActiveKey,
        reset,
        bump,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useProcess(): ProcessState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProcess must be used within ProcessProvider");
  return ctx;
}
