"use client";

import { Building2, ScanLine, Sparkles, Zap } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

type Tab = "trial" | "login" | "enterprise";

export default function AuthLanding() {
  const { signup, login, guest, orgSignup } = useAuth();
  const [tab, setTab] = useState<Tab>("trial");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // shared fields
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [org, setOrg] = useState("");

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  const field = (
    label: string,
    value: string,
    setter: (v: string) => void,
    type = "text",
    placeholder = ""
  ) => (
    <div>
      <label className="mb-1 block text-[11px] uppercase tracking-wide text-muted">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => setter(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-line/20 bg-inset/60 px-3 py-2 text-sm outline-none focus:border-violet"
      />
    </div>
  );

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Left: pitch */}
      <div className="relative hidden flex-col justify-between p-12 lg:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-violet to-gold text-on-accent">
            <ScanLine className="h-5 w-5" />
          </span>
          <span className="text-2xl font-extrabold tracking-tight">Credence</span>
        </div>
        <div className="max-w-md">
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight">
            One platform for every document decision.
          </h1>
          <p className="mt-4 text-muted">
            A vision model reads any document; deterministic rules, ML signals, and a human
            decide. Invoices, receipts, résumés, IDs, contracts and more — start free across
            every domain, then pay only for the one you need.
          </p>
          <div className="mt-8 space-y-3 text-sm text-muted">
            <p className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-gold" /> Free trial credits usable on all domains</p>
            <p className="flex items-center gap-2"><Zap className="h-4 w-4 text-violet" /> Buy credits per-domain — not the whole suite</p>
            <p className="flex items-center gap-2"><Building2 className="h-4 w-4 text-violet" /> Enterprise: one pool, accounts in bulk</p>
          </div>
        </div>
        <p className="text-[11px] text-muted/60">Demo environment · mock billing, no real payments.</p>
      </div>

      {/* Right: auth card */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-5 flex gap-1 rounded-xl border border-line/20 p-1 text-sm">
            {([["trial", "Free trial"], ["login", "Log in"], ["enterprise", "Enterprise"]] as [Tab, string][]).map(
              ([t, label]) => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setError(null); }}
                  className={`flex-1 rounded-lg px-2 py-1.5 transition-colors ${
                    tab === t ? "bg-violet/15 text-text" : "text-muted hover:text-text"
                  }`}
                >
                  {label}
                </button>
              )
            )}
          </div>

          <div className="panel space-y-3">
            {tab === "trial" && (
              <>
                <h2 className="text-lg font-bold">Start your free trial</h2>
                <p className="text-xs text-muted">25 free credits, usable on any domain.</p>
                {field("Name", name, setName)}
                {field("Email", email, setEmail, "email", "you@company.com")}
                {field("Password", password, setPassword, "password")}
                <button disabled={busy} onClick={() => run(() => signup(email, password, name))} className="btn btn-primary w-full">
                  {busy ? "Creating…" : "Create account & start free"}
                </button>
                <button disabled={busy} onClick={() => run(guest)} className="btn btn-ghost w-full text-xs">
                  <Zap className="h-3.5 w-3.5" /> Try instantly (no signup)
                </button>
              </>
            )}
            {tab === "login" && (
              <>
                <h2 className="text-lg font-bold">Welcome back</h2>
                {field("Email", email, setEmail, "email")}
                {field("Password", password, setPassword, "password")}
                <button disabled={busy} onClick={() => run(() => login(email, password))} className="btn btn-primary w-full">
                  {busy ? "Signing in…" : "Log in"}
                </button>
              </>
            )}
            {tab === "enterprise" && (
              <>
                <h2 className="text-lg font-bold">Create an organization</h2>
                <p className="text-xs text-muted">Shared credit pool + add member accounts in bulk.</p>
                {field("Organization name", org, setOrg)}
                {field("Admin name", name, setName)}
                {field("Admin email", email, setEmail, "email")}
                {field("Password", password, setPassword, "password")}
                <button disabled={busy} onClick={() => run(() => orgSignup(org, email, password, name))} className="btn btn-primary w-full">
                  {busy ? "Creating…" : "Create organization"}
                </button>
              </>
            )}
            {error && (
              <div className="rounded-lg border border-red/50 bg-red/10 px-3 py-2 text-xs text-red">{error}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
