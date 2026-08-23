import type {
  ActivityItem,
  ApproveResponse,
  AuthPayload,
  Billing,
  DomainInfo,
  Extraction,
  LedgerRecord,
  ProcessResponse,
  Stats,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "verdict-token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}
function authHeader(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function safeDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
  } catch {
    return "";
  }
}

// ---- auth / billing ----
export async function signup(email: string, password: string, name: string): Promise<AuthPayload> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || "Signup failed");
  return res.json();
}
export async function login(email: string, password: string): Promise<AuthPayload> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || "Login failed");
  return res.json();
}
export async function guest(): Promise<AuthPayload> {
  const res = await fetch(`${API_BASE}/auth/guest`, { method: "POST" });
  if (!res.ok) throw new Error("Could not start trial");
  return res.json();
}
export async function orgSignup(
  org_name: string, admin_email: string, admin_password: string, admin_name: string
): Promise<AuthPayload> {
  const res = await fetch(`${API_BASE}/org/signup`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ org_name, admin_email, admin_password, admin_name }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || "Org signup failed");
  return res.json();
}
export async function me(): Promise<{ user: AuthPayload["user"]; billing: Billing }> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeader(), cache: "no-store" });
  if (!res.ok) throw new Error("unauthorized");
  return res.json();
}
export async function getBilling(): Promise<Billing> {
  const res = await fetch(`${API_BASE}/billing`, { headers: authHeader(), cache: "no-store" });
  if (!res.ok) throw new Error("unauthorized");
  return res.json();
}
export async function purchaseCredits(domain: string, credits: number): Promise<Billing> {
  const res = await fetch(`${API_BASE}/billing/purchase`, {
    method: "POST", headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ domain, credits }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || "Purchase failed");
  return res.json();
}
export async function addMembers(
  members: { email: string; name: string }[]
): Promise<{ created: { email: string; status: string }[] }> {
  const res = await fetch(`${API_BASE}/org/members`, {
    method: "POST", headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ members }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || "Failed to add members");
  return res.json();
}

// ---- core ----
export async function getDomains(): Promise<DomainInfo[]> {
  const res = await fetch(`${API_BASE}/domains`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Domains failed (${res.status})`);
  return (await res.json()).domains;
}

export async function processDocument(
  file: File, domain: string, secondInput?: string
): Promise<ProcessResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("domain", domain || "auto");
  if (secondInput) form.append("second_input", secondInput);
  const res = await fetch(`${API_BASE}/process`, { method: "POST", body: form, headers: authHeader() });
  if (!res.ok) {
    const err: any = new Error((await safeDetail(res)) || `Processing failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function approveDocument(
  domain: string, extraction: Extraction, mockAction: string
): Promise<ApproveResponse> {
  const res = await fetch(`${API_BASE}/approve`, {
    method: "POST", headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ domain, extraction, mock_action: mockAction }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || `Approval failed (${res.status})`);
  return res.json();
}

export async function draftQuery(domain: string, extraction: Extraction): Promise<{ draft: string; changed: boolean }> {
  const res = await fetch(`${API_BASE}/draft-query`, {
    method: "POST", headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ domain, extraction }),
  });
  if (!res.ok) throw new Error(`Draft failed (${res.status})`);
  return res.json();
}

export interface AskResponse {
  answer: string;
  nav?: string;
  suggestions?: string[];
}
export async function askAssistant(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/assistant`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error((await safeDetail(res)) || `Assistant failed (${res.status})`);
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
export async function getLog(): Promise<LedgerRecord[]> {
  const res = await fetch(`${API_BASE}/log`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Log failed (${res.status})`);
  return (await res.json()).records;
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
