import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      // Keeps the dashboard on a same-origin path during development.
      // Override with VITE_API_TARGET if the backend runs elsewhere.
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
