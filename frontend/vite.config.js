import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  if (mode === 'production') {
    if (!env.VITE_API_URL) throw new Error('VITE_API_URL is required for production builds')
    if (new URL(env.VITE_API_URL).protocol !== 'https:') throw new Error('Production VITE_API_URL must use HTTPS')
  }
  return { plugins: [react()], server: { port: 3000, proxy: {
    '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
  } } }
})
