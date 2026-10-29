/** Adapted from Paydirt (MIT, rtulloh): see docs/ATTRIBUTION.md. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        field: { green: '#2d5a27', stripe: '#3d7a37' },
        board: { bg: '#D2691E', border: '#8B4513' },
        panel: { bg: '#F5DEB3', border: '#8B4513' },
      },
      fontFamily: {
        scoreboard: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        heading: ['system-ui', 'sans-serif'],
        body: ['system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
