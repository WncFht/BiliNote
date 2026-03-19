import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import { getManualChunkName } from './build/manualChunks'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd() + '/../')

  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://localhost:8000'
  const port = parseInt(env.VITE_FRONTEND_PORT || '3015', 10)
  const proxy = {
    '/api': {
      target: apiBaseUrl,
      changeOrigin: true,
      rewrite: (requestPath: string) => requestPath.replace(/^\/api/, '/api'),
    },
    '/static': {
      target: apiBaseUrl,
      changeOrigin: true,
      rewrite: (requestPath: string) => requestPath.replace(/^\/static/, '/static'),
    },
  }

  return {
    base: './',
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: getManualChunkName,
        },
      },
    },
    server: {
      host: '0.0.0.0',
      port: port,
      allowedHosts: true, // 允许任意域名访问
      proxy,
    },
    preview: {
      host: '0.0.0.0',
      port,
      proxy,
    },
  }
})
