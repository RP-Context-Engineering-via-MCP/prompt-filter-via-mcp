/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#4F46E5', // indigo-600
          hover: '#4338CA',   // indigo-700
          dark: '#3730A3',    // indigo-800
          light: '#E0E7FF',   // indigo-100
          subtle: '#EEF2FF',  // indigo-50
        },
        memora: {
          bg: '#F8FAFC',      // slate-50
          blue: '#4F46E5',    // indigo-600
          card: '#FFFFFF',
          accent: '#6366F1',  // indigo-500
        },
        sidebar: {
          bg: '#FFFFFF',
          text: '#64748B',    // slate-500
          active: '#4338CA',  // indigo-700
          hover: '#EEF2FF',   // indigo-50
          border: '#F1F5F9',  // slate-100
        }
      },
      boxShadow: {
        'indigo-sm': '0 1px 3px 0 rgb(99 102 241 / 0.15)',
        'indigo-md': '0 4px 12px 0 rgb(99 102 241 / 0.2)',
        'indigo-lg': '0 10px 25px -3px rgb(99 102 241 / 0.25)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.15s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
