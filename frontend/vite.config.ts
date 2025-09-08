import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.REACT_DEV_PORT || '3000'),
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/login': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/register': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/logout': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/reset': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/forgot': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      },
      '/change': {
        target: `http://localhost:${process.env.FLASK_PORT || '8081'}`,
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: '../src/static/dist',
    emptyOutDir: true,
  }
})
