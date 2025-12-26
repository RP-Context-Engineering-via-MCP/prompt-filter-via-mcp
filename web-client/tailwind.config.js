/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#7e22ce', // purple-700
          hover: '#6b21a8',   // purple-800
          light: '#d8b4fe',   // purple-300
        }
      }
    },
  },
  plugins: [],
}
