// D:\lazordy\lazordy\tailwind.config.js

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './django_project/templates/**/*.html', // For project-level templates
    './inventory/templates/**/*.html',
    './reports/templates/**/*.html', // <--- ADD THIS LINE FOR YOUR REPORTS APP
    // "./*.html", // You can keep this if you have .html files directly in your root, but often not needed for Django projects
    // "./src/**/*.{js,jsx,ts,tsx,vue,html}", // Keep this if you have a separate JS/frontend build process
  ],
  darkMode: 'class', // <-- This is fine, keep it.
  theme: {
    extend: {},
  },
  plugins: [],
}