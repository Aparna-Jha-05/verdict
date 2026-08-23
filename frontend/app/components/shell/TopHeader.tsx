"use client";

import { CreditCard, LogOut, Menu, Search } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import ThemeToggle from "./ThemeToggle";

const TITLES: Record<string, { eyebrow: string; title: string }> = {
  "/": { eyebrow: "Overview", title: "Dashboard" },
  "/review": { eyebrow: "Human approval gate", title: "Review" },
  "/ledger": { eyebrow: "Approved records", title: "Ledger" },
  "/audit": { eyebrow: "Activity trail", title: "Audit" },
  "/billing": { eyebrow: "Plan & credits", title: "Billing" },
};

function creditsLabel(billing: ReturnType<typeof useAuth>["billing"]): string {
  if (!billing) return "—";
  if (billing.org) return `${billing.org.pooled_credits} pool`;
  if (billing.account_type === "trial") return `${billing.trial_credits} trial`;
  const sum = Object.values(billing.domain_credits).reduce((a, b) => a + b, 0);
  return `${sum} credits`;
}

export default function TopHeader({
  onOpenPalette,
  onOpenNav,
}: {
  onOpenPalette: () => void;
  onOpenNav: () => void;
}) {
  const pathname = usePathname();
  const { user, billing, logout } = useAuth();
  const key = pathname === "/" ? "/" : "/" + pathname.split("/")[1];
  const meta = TITLES[key] || TITLES["/"];

  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line/10 bg-transparent px-4 py-3 backdrop-blur-md md:px-8">
      <button
        onClick={onOpenNav}
        className="grid h-9 w-9 place-items-center rounded-lg border border-line/20 text-muted md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium uppercase tracking-widest text-muted">{meta.eyebrow}</p>
        <h1 className="truncate text-xl font-extrabold tracking-tight md:text-2xl">{meta.title}</h1>
      </div>

      <Link
        href="/billing"
        className="flex items-center gap-1.5 rounded-lg border border-gold/30 bg-gold/5 px-2.5 py-1.5 text-xs font-semibold text-gold"
        title="Plan & credits"
      >
        <CreditCard className="h-3.5 w-3.5" />
        {creditsLabel(billing)}
      </Link>

      <button
        onClick={onOpenPalette}
        className="hidden items-center gap-2 rounded-lg border border-line/20 px-3 py-2 text-xs text-muted hover:text-text sm:flex"
      >
        <Search className="h-3.5 w-3.5" />
        <kbd className="rounded bg-white/5 px-1.5 py-0.5 text-[10px]">⌘K</kbd>
      </button>

      <ThemeToggle />

      {user && (
        <div className="flex items-center gap-2">
          <span className="hidden text-xs text-muted sm:block" title={user.email}>
            {user.name}
          </span>
          <button
            onClick={logout}
            className="grid h-9 w-9 place-items-center rounded-lg border border-line/20 text-muted hover:text-red"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      )}
    </header>
  );
}
