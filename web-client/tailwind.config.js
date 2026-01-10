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
        },
        memora: {
          bg: '#FAFBFF',
          blue: '#4F46E5',
          card: '#FFFFFF',
        },
        sidebar: {
          text: '#64748B',
          active: '#4338CA', // Indigo-700
          hover: '#E0E7FF',  // Indigo-100
        }
      }
    },
  },
  plugins: [],
}
