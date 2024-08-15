/** @type {import('tailwindcss').Config} */
module.exports = {
  purge: [
    './**/templates/*.html',
  ],
  content: [],
  theme: {
    extend: {
      colors: {
        rioRed: 'rgba(255, 89, 86, 1)',
        rioRedDark: 'rgba(204, 71, 68, 1)',
      }
    },
  },
  plugins: [],
}
