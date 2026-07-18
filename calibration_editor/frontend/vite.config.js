import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/niches':    'http://localhost:8765',
      '/layout':    'http://localhost:8765',
      '/render':    'http://localhost:8765',
      '/templates': 'http://localhost:8765',
    }
  }
})
