/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{svelte,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        clinical: {
          bg: "#FAF9F6",
          card: "#FFFFFF",
          border: "#E7E5E4",
          primary: "#0F766E",
          primaryHover: "#0D9488",
          primaryLight: "#F0FDFA",
          ink: "#1C1917",
          muted: "#78716C",
        },
      },
      lineHeight: {
        golden: "1.618",
      },
    },
  },
  plugins: [],
};
