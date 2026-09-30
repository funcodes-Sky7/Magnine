import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // Only read .env from the frontend directory (not backend/.env)
  envDir: '.',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
    watch: {
      // Exclude backend and node_modules from file watching to prevent
      // infinite restart loops triggered by backend file changes
      ignored: [
        '**/backend/**',
        '**/__pycache__/**',
        '**/*.pyc',
      ],
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
