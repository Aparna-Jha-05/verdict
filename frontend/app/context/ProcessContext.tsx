"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useState } from "react";
import { approveInvoice, processInvoice } from "../lib/api";
import type {
  ApproveResponse,
  Extraction,
  ProcessResponse,
  ScalarKey,
} from "../lib/types";

interface ProcessState {
  fileName: string | null;
  processing: boolean;
  resp: ProcessResponse | null;
  extraction: Extraction | null;
  error: string | null;
  approved: ApproveResponse | null;
  activeKey: string | null;
  processFile: (file: File, navigate?: boolean) => Promise<void>;
  editField: (key: ScalarKey, value: string) => void;
  approve: () => Promise<void>;
  setActiveKey: (k: string | null) => void;
  reset: () => void;
  bump: number; // increments after approve so lists refetch
}

const Ctx = createContext<ProcessState | null>(null);

export function ProcessProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [fileName, setFileName] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [resp, setResp] = useState<ProcessResponse | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approved, setApproved] = useState<ApproveResponse | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  const processFile = useCallback(
    async (file: File, navigate = true) => {
      setProcessing(true);
      setError(null);
      setResp(null);
      setExtraction(null);
      setApproved(null);
      setActiveKey(null);
      setFileName(file.name);
      if (navigate) router.push("/review");
      try {
        const r = await processInvoice(file);
        setResp(r);
        setExtraction(r.extraction);
        setBump((b) => b + 1);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Something went wrong.");
      } finally {
        setProcessing(false);
      }
    },
    [router]
  );

  const editField = useCallback((key: ScalarKey, value: string) => {
    setExtraction((prev) =>
      prev ? { ...prev, [key]: { ...prev[key], value } } : prev
    );
  }, []);

  const approve = useCallback(async () => {
    if (!extraction) return;
    const r = await approveInvoice(extraction);
    setApproved(r);
    setBump((b) => b + 1);
  }, [extraction]);

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
