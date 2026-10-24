import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f0f13',
        surface: '#1a1a24',
        surface2: '#22222f',
        border: 'rgba(255,255,255,0.08)',
        text: '#f0f0f5',
        muted: '#7a7a90',
      },
    },
  },
  plugins: [],
}
export default config
