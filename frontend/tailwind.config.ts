import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F7F5F0",
        ink: {
          DEFAULT: "#14213D",
          soft: "#5B6478",
          faint: "#8A93A6",
        },
        hairline: "#E4E0D5",
        teal: {
          DEFAULT: "#0F766E",
          dark: "#0B5D56",
          wash: "#E6F2F0",
        },
        red: {
          brand: "#B4232A",
          wash: "#F9ECEC",
        },
        amber: {
          brand: "#B54708",
          wash: "#FBF0E3",
        },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "Segoe UI", "sans-serif"],
        mono: ["var(--font-mono)", "Consolas", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
