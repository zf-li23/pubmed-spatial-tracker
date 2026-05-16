import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(() => ({
  plugins: [react()],
  // 默认 base='/', GitHub Pages 部署时通过 VITE_BASE 环境变量覆盖
  base: process.env.VITE_BASE || '/',
}))