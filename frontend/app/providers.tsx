"use client";

import { ProcessProvider } from "./context/ProcessContext";
import { ThemeProvider } from "./context/ThemeContext";
import { TourProvider } from "./context/TourContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <TourProvider>
        <ProcessProvider>{children}</ProcessProvider>
      </TourProvider>
    </ThemeProvider>
  );
}
