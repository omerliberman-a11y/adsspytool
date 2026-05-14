import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx,js,jsx,md,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0b",
        panel: "#121214",
        border: "#23232a",
        muted: "#8b8b94",
        ink: "#ededf0",
        accent: "#7c5cff",
        good: "#3ecf8e",
        warn: "#f6c844",
        bad: "#ef4444",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
