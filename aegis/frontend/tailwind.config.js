/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        aegis: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        danger:  { DEFAULT: '#ef4444', light: '#fef2f2' },
        warning: { DEFAULT: '#f59e0b', light: '#fffbeb' },
        success: { DEFAULT: '#10b981', light: '#ecfdf5' },
        surface: '#f8f8fc',
        card:    '#ffffff',
        border:  '#e7e5ef',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow':   'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'float':        'float 6s ease-in-out infinite',
        'shimmer':      'shimmer 2s linear infinite',
      },
      keyframes: {
        float: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%':     { transform: 'translateY(-8px)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
      },
      boxShadow: {
        glow:       '0 0 20px rgba(99,102,241,0.3)',
        'glow-red': '0 0 20px rgba(239,68,68,0.3)',
        'glow-grn': '0 0 20px rgba(16,185,129,0.3)',
      },
    },
  },
  plugins: [],
}
