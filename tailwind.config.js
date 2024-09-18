/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html',   // Path to your Django templates
    './app/static/js/**/*.js',     // Path to your JavaScript (if any uses Tailwind classes)
  ],
  theme: {
    extend: {
      colors: {
        rioRed: 'rgba(255, 89, 86, 1)',
        rioRedDark: 'rgba(204, 71, 68, 1)',
      },
    },
  },
  plugins: [],
};