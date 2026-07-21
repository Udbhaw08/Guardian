/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        cta: "hsl(var(--cta))",
        panel: {
          header: "hsl(var(--panel-header))",
          inset: "hsl(var(--panel-inset))",
          raised: "hsl(var(--card-raised))",
        },
        // Pastel glass accents (image-1 style mint/cyan/lavender tabs & tiles) —
        // decorative surface tints only, never used for status/data encoding.
        mint: {
          DEFAULT: "hsl(var(--mint))",
          foreground: "hsl(var(--mint-foreground))",
        },
        cyan: {
          DEFAULT: "hsl(var(--cyan))",
          foreground: "hsl(var(--cyan-foreground))",
        },
        lavender: {
          DEFAULT: "hsl(var(--lavender))",
          foreground: "hsl(var(--lavender-foreground))",
        },
        // Semantic decision/severity tokens (used across badges + charts).
        // Use the /10, /15 etc. opacity modifiers (e.g. bg-allow/10) for soft-tint
        // pill and chip backgrounds instead of separate "-soft" color keys.
        allow: "hsl(var(--allow))",
        warn: "hsl(var(--warn))",
        block: "hsl(var(--block))",
      },
      borderRadius: {
        lg: "calc(var(--radius) + 4px)",
        md: "var(--radius)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        shell: "var(--shadow-shell)",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "Segoe UI",
          "Helvetica Neue",
          "Fira Sans",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        mono: ["Fira Code", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
