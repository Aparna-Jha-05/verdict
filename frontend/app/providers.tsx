"use client";

import { AuthProvider } from "./context/AuthContext";
import { ProcessProvider } from "./context/ProcessContext";
import { ThemeProvider } from "./context/ThemeContext";
import { TourProvider } from "./context/TourContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <TourProvider>
          <ProcessProvider>{children}</ProcessProvider>
        </TourProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
