/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        canvas: "#F7F6F0",
        forest: {
          DEFAULT: "#123D32",
          deep: "#092820",
          moss: "#1E5A46",
        },
        civic: {
          lime: "#C7F36B",
          amber: "#F2B84B",
          coral: "#E66B59",
        },
        ink: {
          DEFAULT: "#25352F",
          soft: "#45564F",
          mute: "#819087",
        },
        line: "#E2E7DE",
      },
      boxShadow: {
        card: "0 1px 2px rgba(37,53,47,0.05)",
        pop: "0 16px 40px -12px rgba(9,40,32,0.25)",
      },
    },
  },
  plugins: [],
};
