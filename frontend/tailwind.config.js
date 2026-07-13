/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0A0D12",
        panel: "#12161D",
        panel2: "#171C25",
        line: "#232A35",
        text: "#E8EAED",
        muted: "#7C8896",
        signal: "#3DD68C",
        amber: "#F0A742",
        red: "#FF5C5C",
        blue: "#5B8DEF",
        violet: "#9B7BF5",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
