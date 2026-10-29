import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Adapted from Paydirt (MIT, rtulloh): see docs/ATTRIBUTION.md.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    testTimeout: 30000,
  },
})
