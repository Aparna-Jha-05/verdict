import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Invoice Intelligence — Verify, Catch, Approve",
  description:
    "Vision-first invoice extraction with deterministic validation, fraud detection, and a human approval gate.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="cosmic-bg" aria-hidden />
        <div className="cosmic-glow" aria-hidden />
        {children}
      </body>
    </html>
  );
}
