/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        up: {
          DEFAULT: "#ef4444",
          green: "#10b981",
        },
        down: {
          DEFAULT: "#10b981",
          red: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};
