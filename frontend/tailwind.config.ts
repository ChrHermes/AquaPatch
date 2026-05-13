import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        leaf: '#2f7d57',
        soil: '#7a5230',
        water: '#2374ab'
      }
    }
  },
  plugins: []
} satisfies Config
