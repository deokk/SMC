import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
<<<<<<< HEAD
  server: {port: 5173, strictPort: true},
=======
  server: {
    host: '0.0.0.0', // Make Vite accessible from network
    port: 5173,
    strictPort: true,
    proxy: {
      // 백엔드 API 서버로 요청을 프록시합니다.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/users': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/token': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/route': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/stations': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
       '/predict': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/riders': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/rides': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/friends': { // Add this line
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  },
>>>>>>> backend
  // 등록이 5174로 떠도 되도록 수정
});
