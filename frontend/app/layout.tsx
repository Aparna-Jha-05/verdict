import type { Metadata } from "next";
import AppFrame from "./components/shell/AppFrame";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Credence — Verify, Catch, Approve",
  description:
    "Vision-first invoice extraction with deterministic validation, fraud detection, and a human approval gate.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark">
      <body>
        <div className="cosmic-bg" aria-hidden />
        <div className="cosmic-glow" aria-hidden />
        <Providers>
          <AppFrame>{children}</AppFrame>
        </Providers>
      </body>
    </html>
  );
}
