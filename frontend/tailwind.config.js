/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,jsx,ts,tsx}',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      boxShadow: {
        glass: '0 20px 80px rgba(15, 23, 42, 0.35)',
      },
      backgroundImage: {
        'hero-grid': 'radial-gradient(circle at 1px 1px, rgba(148,163,184,.12) 1px, transparent 0)',
      },
    },
  },
  plugins: [],
}