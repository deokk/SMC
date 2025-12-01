import { useEffect, useRef } from "react";
import useKakaoLoader from "../hooks/useKaKaoLoader.js";

export default function KakaoMap() {
  const ref = useRef(null);
  const sdkReady = useKakaoLoader();

  useEffect(() => {
    if (!sdkReady) return;
    if (!window.kakao?.maps) {
      console.error("[KakaoMap] sdkReady인데 window.kakao.maps가 없습니다.");
      return;
    }

    window.kakao.maps.load(() => {
      const center = new window.kakao.maps.LatLng(37.5408, 127.0793);
      const map = new window.kakao.maps.Map(ref.current, { center, level: 4 });
      new window.kakao.maps.Marker({ position: center }).setMap(map);
    });
  }, [sdkReady]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      {!sdkReady && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
          }}
        >
          카카오맵 로딩 중...
        </div>
      )}
      <div ref={ref} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
