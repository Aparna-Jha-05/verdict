"use client";

import {
  ClipboardList,
  LayoutDashboard,
  ScrollText,
  Sparkles,
  X,
  ScanLine,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTour } from "../../context/TourContext";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/review", label: "Review", icon: ScanLine },
  { href: "/ledger", label: "Ledger", icon: ScrollText },
  { href: "/audit", label: "Audit", icon: ClipboardList },
];

export default function Sidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();
  const { start } = useTour();

  const nav = (
    <nav className="flex h-full w-64 flex-col gap-1 border-r border-line/15 bg-inset/70 p-4 backdrop-blur-xl">
      <div className="mb-4 flex items-center gap-2.5 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet to-gold text-on-accent">
          <ScanLine className="h-5 w-5" />
        </div>
        <div>
          <div className="text-lg font-extrabold leading-none tracking-tight">
            Verdict
          </div>
          <div className="mt-0.5 text-[10px] uppercase tracking-widest text-muted">
            Invoice Intelligence
          </div>
        </div>
      </div>

      {LINKS.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onClose}
            className={`nav-link ${active ? "nav-link-active" : ""}`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        );
      })}

      <button
        onClick={() => {
          onClose();
          start();
        }}
        className="nav-link mt-auto border border-gold/30 text-gold hover:bg-gold/10"
      >
        <Sparkles className="h-4 w-4" />
        Guided tour
      </button>
      <p className="px-3 pt-2 text-[10px] leading-relaxed text-muted">
        LLM extracts · deterministic rules decide · human approves
      </p>
    </nav>
  );

  return (
    <>
      <aside className="hidden md:block">{nav}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={onClose} />
          <div className="absolute left-0 top-0 h-full">
            <button
              onClick={onClose}
              className="absolute right-2 top-3 z-10 rounded-lg p-1.5 text-muted hover:text-text"
              aria-label="Close navigation"
            >
              <X className="h-5 w-5" />
            </button>
            {nav}
          </div>
        </div>
      )}
    </>
  );
}
