/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eafaf0",
          100: "#cdf0da",
          200: "#9fe3b9",
          300: "#63d08f",
          400: "#34d399",
          500: "#16a34a",
          600: "#0f7c39", // verde Lar Plásticos
          700: "#0c6330",
          800: "#0a4f28",
          900: "#063a1d",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
      },
      keyframes: {
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        pulseRing: {
          "0%": { boxShadow: "0 0 0 0 rgba(220,38,38,0.5)" },
          "70%": { boxShadow: "0 0 0 8px rgba(220,38,38,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(220,38,38,0)" },
        },
        rise: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        blink: "blink 1.1s ease-in-out infinite",
        pulseRing: "pulseRing 1.6s ease-out infinite",
        rise: "rise 0.25s ease-out",
      },
    },
  },
  plugins: [],
};
