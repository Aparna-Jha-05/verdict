import type { ApproveResponse, Extraction, ProcessResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

export async function processInvoice(file: File): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/process`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `Processing failed (${res.status})`);
  }
  return res.json();
}

export async function approveInvoice(
  extraction: Extraction
): Promise<ApproveResponse> {
  const res = await fetch(`${API_BASE}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extraction, mock_action: "queued for payment" }),
  });
  if (!res.ok) {
    const detail = await safeDetail(res);
    throw new Error(detail || `Approval failed (${res.status})`);
  }
  return res.json();
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
  } catch {
    return "";
  }
}

export { API_BASE };
