"use client";

import { useEffect, useState } from "react";
import CommandPalette from "./CommandPalette";
import ConnectionFooter from "./ConnectionFooter";
import GuidedTour from "../walkthrough/GuidedTour";
import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem("verdict-nav-collapsed") === "1");
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toggleCollapse = () =>
    setCollapsed((c) => {
      localStorage.setItem("verdict-nav-collapsed", c ? "0" : "1");
      return !c;
    });

  return (
    <div className="flex min-h-screen">
      <Sidebar
        mobileOpen={mobileNav}
        onClose={() => setMobileNav(false)}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopHeader
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenNav={() => setMobileNav(true)}
        />
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8">
          {children}
        </main>
        <ConnectionFooter />
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <GuidedTour />
    </div>
  );
}
