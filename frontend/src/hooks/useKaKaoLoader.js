import { useEffect, useState } from "react";

export default function useKakaoLoader() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
<<<<<<< HEAD
=======
    // For debugging: Log all environment variables Vite is aware of.
    console.log("Vite env variables:", import.meta.env);
    
>>>>>>> backend
    const appkey = import.meta.env.VITE_KAKAO_MAP_APPKEY;

    if (!appkey) {
      console.error("[KakaoMap] VITE_KAKAO_MAP_APPKEY is undefined (.env 위치/재시작 확인)");
      return;
    }

    // 이미 로드되어 있으면 끝
    if (window.kakao?.maps) {
      setReady(true);
      return;
    }

    // 스크립트가 이미 붙어있으면 onload만 기다림
    const existing = document.querySelector('script[data-kakao-sdk="true"]');
    if (existing) {
      existing.addEventListener("load", () => setReady(true), { once: true });
      return;
    }

    // 스크립트 삽입
    const script = document.createElement("script");
    script.dataset.kakaoSdk = "true";
    script.async = true;
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appkey}&autoload=false&libraries=services`;

    script.onload = () => setReady(true);
    script.onerror = () => console.error("[KakaoMap] SDK script load failed (도메인/네트워크 확인)");

    document.head.appendChild(script);
  }, []);

  return ready;
}
