/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // Deep charcoal base
        base: {
          950: '#0a0a0f',
          900: '#0d0d14',
          850: '#101018',
          800: '#13131d',
          750: '#161624',
          700: '#1a1a2e',
        },
        // Brand gradient colors
        brand: {
          blue: '#3b82f6',
          indigo: '#6366f1',
          violet: '#8b5cf6',
          teal: '#14b8a6',
          cyan: '#06b6d4',
        },
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
        'brand-gradient-teal': 'linear-gradient(135deg, #14b8a6, #6366f1)',
        'aurora': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.15), transparent)',
        'aurora-teal': 'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(20,184,166,0.12), transparent)',
        'card-glow': 'radial-gradient(ellipse at top, rgba(99,102,241,0.08), transparent 60%)',
        'stat-glow-blue': 'radial-gradient(ellipse at top left, rgba(59,130,246,0.12), transparent 60%)',
        'stat-glow-amber': 'radial-gradient(ellipse at top left, rgba(245,158,11,0.12), transparent 60%)',
        'stat-glow-emerald': 'radial-gradient(ellipse at top left, rgba(16,185,129,0.12), transparent 60%)',
        'stat-glow-rose': 'radial-gradient(ellipse at top left, rgba(244,63,94,0.12), transparent 60%)',
      },
      keyframes: {
        'count-up': {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.6', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'aurora-shift': {
          '0%, 100%': { opacity: '0.6', transform: 'translateY(0)' },
          '50%': { opacity: '1', transform: 'translateY(-10px)' },
        },
        'slide-right': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'fade-up': {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.92)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'check-pop': {
          '0%': { transform: 'scale(0)', opacity: '0' },
          '60%': { transform: 'scale(1.3)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'ring-fill': {
          '0%': { strokeDashoffset: '283' },
          '100%': { strokeDashoffset: 'var(--target-offset)' },
        },
      },
      animation: {
        'count-up': 'count-up 0.4s ease-out forwards',
        'float': 'float 4s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 2.5s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite linear',
        'aurora-shift': 'aurora-shift 6s ease-in-out infinite',
        'slide-right': 'slide-right 0.3s ease-out',
        'fade-up': 'fade-up 0.4s ease-out',
        'scale-in': 'scale-in 0.25s ease-out',
        'check-pop': 'check-pop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'ring-fill': 'ring-fill 1.2s ease-out forwards',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
        'glass-lg': '0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)',
        'brand-glow': '0 0 20px rgba(99,102,241,0.35), 0 0 40px rgba(99,102,241,0.15)',
        'brand-glow-sm': '0 0 12px rgba(99,102,241,0.4)',
        'teal-glow': '0 0 20px rgba(20,184,166,0.3)',
        'amber-glow': '0 0 20px rgba(245,158,11,0.3)',
        'emerald-glow': '0 0 20px rgba(16,185,129,0.3)',
        'rose-glow': '0 0 20px rgba(244,63,94,0.3)',
        'card-hover': '0 16px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.25)',
        'diff-easy': '0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(16,185,129,0.2), inset 0 -1px 0 rgba(0,0,0,0.3)',
        'diff-medium': '0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(245,158,11,0.2), inset 0 -1px 0 rgba(0,0,0,0.3)',
        'diff-hard': '0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(244,63,94,0.2), inset 0 -1px 0 rgba(0,0,0,0.3)',
      },
      backdropBlur: {
        'glass': '20px',
        'heavy': '40px',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}
