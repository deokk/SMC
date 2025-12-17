import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0", // 외부에서 접속 가능하게 설정
    port: 5173,
    strictPort: true, // 5173 포트가 사용 중이면 에러 발생 (원하시면 false로 변경 가능)
    proxy: {
      // 백엔드 API 서버(FastAPI/Django 등)로 요청을 넘겨주는 설정
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/users": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/token": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/route": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/stations": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/predict": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/riders": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/rides": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/friends": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
