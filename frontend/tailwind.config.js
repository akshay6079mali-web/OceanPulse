/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'ocean-bg': '#18181B',
        'hud-bg': 'rgba(36,36,39,0.95)',
        'hud-input': '#1E1E22',
        'hud-border': '#27272A',
        'hud-hover': '#3F3F46',
        'primary-text': '#E4E4E7',
        'muted-text': '#A1A1AA',
        'cyber-cyan': '#06B6D4',
        'action-cobalt': '#2563EB',
        'op-emerald': '#10B981',
        'anomaly-amber': '#F59E0B',
        'critical-red': '#EF4444'
      },
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        'mono': ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
