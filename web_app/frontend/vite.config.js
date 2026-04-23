import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // Use repository subpath only for production (GitHub Pages).
  base: mode === 'production' ? '/pubmed-spatial-tracker/' : '/',
}))
