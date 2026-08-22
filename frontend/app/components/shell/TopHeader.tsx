"use client";

import { Menu, Search } from "lucide-react";
import { usePathname } from "next/navigation";
import ThemeToggle from "./ThemeToggle";

const TITLES: Record<string, { eyebrow: string; title: string }> = {
  "/": { eyebrow: "Overview", title: "Dashboard" },
  "/review": { eyebrow: "Human approval gate", title: "Review" },
  "/ledger": { eyebrow: "Approved invoices", title: "Ledger" },
  "/audit": { eyebrow: "Activity trail", title: "Audit" },
};

export default function TopHeader({
  onOpenPalette,
  onOpenNav,
}: {
  onOpenPalette: () => void;
  onOpenNav: () => void;
}) {
  const pathname = usePathname();
  const key = pathname === "/" ? "/" : "/" + pathname.split("/")[1];
  const meta = TITLES[key] || TITLES["/"];

  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-line/15 bg-bg/70 px-4 py-3 backdrop-blur-xl md:px-8">
      <button
        onClick={onOpenNav}
        className="grid h-9 w-9 place-items-center rounded-lg border border-line/20 text-muted md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-4 w-4" />
      </button>

      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium uppercase tracking-widest text-muted">
          {meta.eyebrow}
        </p>
        <h1 className="truncate text-xl font-extrabold tracking-tight md:text-2xl">
          {meta.title}
        </h1>
      </div>

      <button
        onClick={onOpenPalette}
        className="hidden items-center gap-2 rounded-lg border border-line/20 px-3 py-2 text-xs text-muted hover:text-text sm:flex"
      >
        <Search className="h-3.5 w-3.5" />
        Search
        <kbd className="rounded bg-white/5 px-1.5 py-0.5 text-[10px]">⌘K</kbd>
      </button>
      <button
        onClick={onOpenPalette}
        className="grid h-9 w-9 place-items-center rounded-lg border border-line/20 text-muted sm:hidden"
        aria-label="Search"
      >
        <Search className="h-4 w-4" />
      </button>
      <ThemeToggle />
    </header>
  );
}
