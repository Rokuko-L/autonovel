import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5175,
    // FastAPI backend lands in ../server.py later; mock client is used until then
    proxy: {
      '/api': 'http://127.0.0.1:8600',
    },
  },
})
