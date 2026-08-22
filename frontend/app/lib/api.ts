import type {
  ActivityItem,
  ApproveResponse,
  Extraction,
  LedgerRow,
  ProcessResponse,
  Stats,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function safeDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
  } catch {
    return "";
  }
}

export async function processInvoice(file: File): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/process`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await safeDetail(res)) || `Processing failed (${res.status})`);
  return res.json();
}

export async function approveInvoice(extraction: Extraction): Promise<ApproveResponse> {
  const res = await fetch(`${API_BASE}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extraction, mock_action: "queued for payment" }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || `Approval failed (${res.status})`);
  return res.json();
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Stats failed (${res.status})`);
  return res.json();
}

export async function getActivity(limit = 100): Promise<ActivityItem[]> {
  const res = await fetch(`${API_BASE}/activity?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Activity failed (${res.status})`);
  return (await res.json()).activity;
}

export async function getLog(): Promise<LedgerRow[]> {
  const res = await fetch(`${API_BASE}/log`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Log failed (${res.status})`);
  return (await res.json()).invoices;
}

export async function draftVendorQuery(
  extraction: Extraction
): Promise<{ draft: string; bank_changed: boolean }> {
  const res = await fetch(`${API_BASE}/draft-vendor-query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extraction }),
  });
  if (!res.ok) throw new Error(`Draft failed (${res.status})`);
  return res.json();
}

export async function getHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export { API_BASE };
