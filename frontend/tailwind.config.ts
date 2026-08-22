import type { Config } from "tailwindcss";

// Tokens use RGB channels so Tailwind opacity modifiers (e.g. bg-violet/15)
// work, and so light/dark themes swap by redefining the channels in globals.css.
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--c-bg) / <alpha-value>)",
        card: "rgb(var(--c-card) / <alpha-value>)",
        surface: "rgb(var(--c-surface) / <alpha-value>)",
        inset: "rgb(var(--c-inset) / <alpha-value>)",
        line: "rgb(var(--c-line) / <alpha-value>)",
        text: "rgb(var(--c-text) / <alpha-value>)",
        muted: "rgb(var(--c-muted) / <alpha-value>)",
        violet: "rgb(var(--c-violet) / <alpha-value>)",
        gold: "rgb(var(--c-gold) / <alpha-value>)",
        green: "rgb(var(--c-green) / <alpha-value>)",
        amber: "rgb(var(--c-amber) / <alpha-value>)",
        red: "rgb(var(--c-red) / <alpha-value>)",
        "on-accent": "rgb(var(--c-on-accent) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.1rem",
      },
      keyframes: {
        pop: {
          "0%": { transform: "scale(0.9)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        drift: { from: { transform: "translateY(0)" }, to: { transform: "translateY(-700px)" } },
        spin: { to: { transform: "rotate(360deg)" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseGold: {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(245,196,81,0.4)" },
          "50%": { boxShadow: "0 0 0 7px rgba(245,196,81,0)" },
        },
      },
      animation: {
        pop: "pop 0.35s ease",
        drift: "drift 90s linear infinite",
        spin: "spin 0.8s linear infinite",
        shimmer: "shimmer 1.6s infinite",
        pulseGold: "pulseGold 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
