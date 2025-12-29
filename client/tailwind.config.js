/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        poppins: ['Poppins', 'sans-serif'],
        dm: ['DM Sans', 'sans-serif'],
      },
      colors: {
        brand: {
          primary: '#2E571C',
          secondary: '#547023',
          muted: '#E8F1E4',
          dark: '#1F3A12',
        },
        accent: {
          primary: '#000000',
          success: '#10B981',
          warning: '#F59E0B',
          error: '#EF4444',
        },
      },
    },
  },
  plugins: [],
}
