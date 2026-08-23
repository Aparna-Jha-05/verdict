"use client";

import { Building2, Check, CreditCard, Plus } from "lucide-react";
import { useState } from "react";
import DomainIcon from "../components/shell/DomainIcon";
import { useAuth } from "../context/AuthContext";
import { useProcess } from "../context/ProcessContext";
import { addMembers, purchaseCredits } from "../lib/api";

const PACKS = [50, 100, 500];

export default function BillingPage() {
  const { billing, user, refreshBilling } = useAuth();
  const { domains } = useProcess();
  const [buying, setBuying] = useState<string | null>(null);
  const [members, setMembers] = useState("");
  const [memberResult, setMemberResult] = useState<string | null>(null);
  const [busyMembers, setBusyMembers] = useState(false);

  const buy = async (domain: string, credits: number) => {
    setBuying(domain + credits);
    try {
      await purchaseCredits(domain, credits);
      await refreshBilling();
    } finally {
      setBuying(null);
    }
  };

  const provision = async () => {
    const list = members
      .split(/[\n,]+/)
      .map((e) => e.trim())
      .filter(Boolean)
      .map((email) => ({ email, name: email.split("@")[0] }));
    if (!list.length) return;
    setBusyMembers(true);
    setMemberResult(null);
    try {
      const r = await addMembers(list);
      const ok = r.created.filter((m) => m.status === "created").length;
      setMemberResult(`${ok} of ${r.created.length} member accounts created.`);
      setMembers("");
    } catch (e) {
      setMemberResult(e instanceof Error ? e.message : "Failed.");
    } finally {
      setBusyMembers(false);
    }
  };

  if (!billing) return null;
  const isEnterprise = !!billing.org;
  const isAdmin = user?.account_type === "enterprise_admin";

  return (
    <div className="space-y-5">
      {/* Plan summary */}
      <div className="panel">
        <div className="panel-title">
          <CreditCard className="h-4 w-4 text-gold" />
          Your Plan
        </div>
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted">Account</div>
            <div className="text-lg font-bold capitalize">{billing.account_type.replace("_", " ")}</div>
          </div>
          {isEnterprise ? (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Org pool</div>
              <div className="text-lg font-bold tabular-nums">{billing.org!.pooled_credits} credits</div>
              <div className="text-[11px] text-muted">{billing.org!.name}</div>
            </div>
          ) : (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-muted">Free trial credits</div>
              <div className="text-lg font-bold tabular-nums">{billing.trial_credits}</div>
              <div className="text-[11px] text-muted">usable on any domain</div>
            </div>
          )}
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted">Cost</div>
            <div className="text-lg font-bold tabular-nums">{billing.cost_per_doc}/document</div>
          </div>
        </div>
        <p className="mt-3 text-[11px] text-muted/70">Demo environment — purchases are mocked, no real payment is taken.</p>
      </div>

      {/* Per-domain credits */}
      {!isEnterprise && (
        <div className="panel">
          <div className="panel-title">
            Buy credits per domain
            <span className="font-normal normal-case tracking-normal text-muted">
              · pay only for the domain you need
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {domains
              .filter((d) => d.name !== "generic")
              .map((d) => {
                const owned = billing.domain_credits[d.name] || 0;
                return (
                  <div key={d.name} className="rounded-xl border border-line/20 bg-white/[0.02] p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="grid h-8 w-8 place-items-center rounded-lg bg-violet/15 text-violet">
                        <DomainIcon name={d.icon} className="h-4 w-4" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold">{d.label}</div>
                        <div className="text-[11px] text-muted">
                          {owned > 0 ? `${owned} credits owned` : "no credits yet"}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1.5">
                      {PACKS.map((c) => (
                        <button
                          key={c}
                          disabled={buying === d.name + c}
                          onClick={() => buy(d.name, c)}
                          className="chip flex-1 justify-center"
                        >
                          {buying === d.name + c ? "…" : `+${c}`}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Enterprise member provisioning */}
      {isAdmin && (
        <div className="panel">
          <div className="panel-title">
            <Building2 className="h-4 w-4 text-violet" />
            Add member accounts in bulk
          </div>
          <p className="mb-2 text-xs text-muted">
            Paste member emails (comma or newline separated). Each gets an account under your org, sharing the pool.
          </p>
          <textarea
            value={members}
            onChange={(e) => setMembers(e.target.value)}
            rows={4}
            placeholder="alice@acme.com, bob@acme.com&#10;carol@acme.com"
            className="w-full resize-y rounded-lg border border-line/20 bg-inset/60 px-3 py-2 text-sm outline-none focus:border-violet"
          />
          <div className="mt-2 flex items-center gap-3">
            <button disabled={busyMembers} onClick={provision} className="btn btn-primary text-sm">
              <Plus className="h-4 w-4" /> {busyMembers ? "Provisioning…" : "Provision accounts"}
            </button>
            {memberResult && (
              <span className="flex items-center gap-1 text-xs text-green">
                <Check className="h-3.5 w-3.5" /> {memberResult}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
