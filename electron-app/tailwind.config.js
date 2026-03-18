/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#60cdff',
          hover: '#78d4ff',
          dark: '#60cdff',
          light: '#0078d4',
        },
        surface: {
          base: 'var(--surface-base)',
          raised: 'var(--surface-raised)',
          overlay: 'var(--surface-overlay)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          DEFAULT: 'var(--border-default)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
      },
      fontFamily: {
        sans: ['Segoe UI Variable', 'Segoe UI', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'caption': ['12px', { lineHeight: '16px' }],
        'body': ['14px', { lineHeight: '20px' }],
        'subtitle': ['16px', { lineHeight: '22px' }],
        'title': ['20px', { lineHeight: '28px' }],
        'display': ['28px', { lineHeight: '36px' }],
      },
      borderRadius: {
        'fluent': '8px',
        'fluent-lg': '12px',
      },
      boxShadow: {
        'fluent': '0 2px 4px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)',
        'fluent-lg': '0 8px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.06)',
        'fluent-focus': '0 0 0 2px var(--accent-color)',
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-up': 'slideUp 250ms ease-out',
        'scale-in': 'scaleIn 200ms ease-out',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
};
