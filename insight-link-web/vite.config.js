import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/admin': 'http://localhost:8080',
      '/teacher': 'http://localhost:8080',
      '/school-hierarchy': 'http://localhost:8080',
      '/student': 'http://localhost:8080',
      '/user': 'http://localhost:8080',
      '/message': 'http://localhost:8080'
    }
  }
})
