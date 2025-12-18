import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Trading colors
        profit: '#10b981',
        loss: '#ef4444',
        neutral: '#6b7280',
        // Signal strength
        strong: '#22c55e',
        moderate: '#eab308',
        weak: '#f97316',
      },
    },
  },
  plugins: [],
}
export default config
