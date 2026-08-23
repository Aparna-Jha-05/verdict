"use client";

import {
  ClipboardList,
  CreditCard,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
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
  { href: "/billing", label: "Billing", icon: CreditCard },
];

export default function Sidebar({
  mobileOpen,
  onClose,
  collapsed = false,
  onToggleCollapse,
}: {
  mobileOpen: boolean;
  onClose: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const pathname = usePathname();
  const { start } = useTour();

  // `mini` = desktop collapsed view (icons only). Mobile drawer is always full.
  const nav = (mini: boolean) => (
    <nav
      className={`flex h-full flex-col gap-1 border-r border-line/15 bg-inset/70 p-3 backdrop-blur-xl transition-[width] duration-200 ${
        mini ? "w-16 items-center" : "w-64"
      }`}
    >
      <div className={`mb-4 flex items-center gap-2.5 ${mini ? "justify-center px-0" : "px-2"}`}>
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-violet to-gold text-on-accent">
          <ScanLine className="h-5 w-5" />
        </div>
        {!mini && (
          <div>
            <div className="text-lg font-extrabold leading-none tracking-tight">Verdict</div>
            <div className="mt-0.5 text-[10px] uppercase tracking-widest text-muted">
              Document Intelligence
            </div>
          </div>
        )}
      </div>

      {LINKS.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onClose}
            title={mini ? label : undefined}
            className={`nav-link ${active ? "nav-link-active" : ""} ${mini ? "w-11 justify-center px-0" : ""}`}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {!mini && label}
          </Link>
        );
      })}

      <button
        onClick={() => {
          onClose();
          start();
        }}
        title={mini ? "Guided tour" : undefined}
        className={`nav-link mt-auto border border-gold/30 text-gold hover:bg-gold/10 ${
          mini ? "w-11 justify-center px-0" : ""
        }`}
      >
        <Sparkles className="h-4 w-4 shrink-0" />
        {!mini && "Guided tour"}
      </button>

      {/* Desktop collapse toggle */}
      {onToggleCollapse && (
        <button
          onClick={onToggleCollapse}
          title={mini ? "Expand" : "Collapse"}
          className={`nav-link hidden text-muted md:flex ${mini ? "w-11 justify-center px-0" : ""}`}
        >
          {mini ? <PanelLeftOpen className="h-4 w-4" /> : (
            <>
              <PanelLeftClose className="h-4 w-4 shrink-0" /> Collapse
            </>
          )}
        </button>
      )}

      {!mini && (
        <p className="px-3 pt-1 text-[10px] leading-relaxed text-muted">
          AI reads · rules decide · human approves
        </p>
      )}
    </nav>
  );

  return (
    <>
      <aside className="hidden md:block">{nav(collapsed)}</aside>
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
            {nav(false)}
          </div>
        </div>
      )}
    </>
  );
}
