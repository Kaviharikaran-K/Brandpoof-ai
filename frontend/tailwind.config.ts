import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#EBF0EA",
        ink: {
          DEFAULT: "#515654",
          soft: "#6E7473",
          faint: "#8D9390",
        },
        hairline: "#D5DDD7",
        teal: {
          DEFAULT: "#4FB28F",
          dark: "#276B52",
          wash: "#E4F3EC",
        },
        red: {
          brand: "#B4232A",
          wash: "#F8E9E9",
        },
        amber: {
          brand: "#B54708",
          wash: "#FBF0E2",
        },
      },
      fontFamily: {
        serif: ["var(--font-sans)", "Segoe UI", "sans-serif"],
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
