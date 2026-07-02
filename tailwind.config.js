/** Config Tailwind (build local, CSS commite dans static/css/app.css).
 *  Reconstruire apres modification de classes :
 *  npx tailwindcss@3.4.17 -c tailwind.config.js -i static/src/input.css -o static/css/app.css --minify
 */
module.exports = {
  content: [
    './templates/**/*.html',
    './listings/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        'apple-bg': '#F5F5F7',
        'apple-card': '#FFFFFF',
        'apple-text': '#1D1D1F',
        'apple-gray': '#86868B',
        'apple-blue': '#0071E3',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        apple: '0 4px 24px -1px rgba(0, 0, 0, 0.06), 0 2px 8px -1px rgba(0, 0, 0, 0.04)',
        'apple-hover': '0 12px 40px -4px rgba(0, 0, 0, 0.1), 0 4px 12px -2px rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
};
