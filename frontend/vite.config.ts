import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Calls to /api go to the FastAPI backend
    proxy: { '/api': process.env.API_TARGET ?? 'http://127.0.0.1:8000' },
  },
})
