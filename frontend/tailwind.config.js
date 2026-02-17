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
          50: '#fdf5e6',
          100: '#f7e6c4',
          200: '#f0d49e',
          300: '#e8bf73',
          400: '#e0a94d',
          500: '#D4A853',
          600: '#C4922E',
          700: '#A67B22',
          800: '#8A6518',
          900: '#6E5010',
        },
        sangha: {
          gold: '#D4A853',
          saffron: '#E8893C',
          earth: '#8B6914',
          sage: '#40c057',
          cream: '#F5E6CC',
          amber: '#F0C06E',
        },
        kailasa: {
          bg: '#1a1012',
          bgLight: '#221419',
          surface: '#2d1520',
          surfaceLight: '#3a2030',
          surfaceHover: '#4a2d40',
          border: '#5a3548',
          borderLight: '#6d4458',
          muted: '#9a7585',
          text: '#F5E6CC',
          textSecondary: '#C4A88A',
        },
      },
      backgroundImage: {
        'kailasa-gradient': 'linear-gradient(135deg, #1a1012 0%, #2d1520 50%, #1a1012 100%)',
        'kailasa-card': 'linear-gradient(135deg, rgba(212,168,83,0.08) 0%, rgba(45,21,32,0.9) 100%)',
        'kailasa-card-highlight': 'linear-gradient(135deg, rgba(212,168,83,0.15) 0%, rgba(45,21,32,0.85) 100%)',
        'kailasa-sidebar': 'linear-gradient(180deg, #2a1620 0%, #221419 100%)',
        'kailasa-gold-card': 'linear-gradient(135deg, rgba(212,168,83,0.2) 0%, rgba(139,105,20,0.15) 50%, rgba(45,21,32,0.9) 100%)',
      },
      boxShadow: {
        'warm': '0 4px 24px rgba(212, 168, 83, 0.08)',
        'warm-lg': '0 8px 32px rgba(212, 168, 83, 0.12)',
        'warm-glow': '0 0 20px rgba(212, 168, 83, 0.15)',
      },
    },
  },
  plugins: [],
}
