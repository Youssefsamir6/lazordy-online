/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./*.html",
    "./src/**/*.{js,jsx,ts,tsx,vue,html}",
  ],
  darkMode: 'class', // <-- here!
  theme: {
    extend: {},
  },
  plugins: [],
}
