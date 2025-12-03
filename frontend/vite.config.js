import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {port: 5173, strictPort: true},
  // 등록이 5174로 떠도 되도록 수정
});
