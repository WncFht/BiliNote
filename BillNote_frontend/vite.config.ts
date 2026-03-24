import path from 'path'
import { fileURLToPath } from 'url'

import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, loadEnv } from 'vite'

import { getManualChunkName } from './build/manualChunks'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => {
  const envDir = process.env.DOCKER_BUILD ? __dirname : path.resolve(__dirname, '../')
  const env = loadEnv(mode, envDir)

  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8483'
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
      port,
      allowedHosts: true,
      proxy,
    },
    preview: {
      host: '0.0.0.0',
      port,
      proxy,
    },
  }
})
