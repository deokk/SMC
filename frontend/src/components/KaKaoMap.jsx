import { useEffect, useRef, useState } from "react";
import useKakaoLoader from "../hooks/useKakaoLoader.js";
import "./KakaoMap.css";

export default function KakaoMap({ stations = [] }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const overlaysRef = useRef([]);
  const sdkReady = useKakaoLoader();
  const [mapReady, setMapReady] = useState(false);

  // 지도 생성
  useEffect(() => {
    if (!sdkReady) return;
    if (!window.kakao?.maps) return;

    window.kakao.maps.load(() => {
      if (mapRef.current) {
        setMapReady(true);
        return;
      }

      const center = new window.kakao.maps.LatLng(37.5408, 127.0793);
      mapRef.current = new window.kakao.maps.Map(containerRef.current, {
        center,
        level: 4,
      });
      setMapReady(true);
    });
  }, [sdkReady]);

  // stations 바뀔 때마다 마커 다시 그리기
  useEffect(() => {
    if (!sdkReady) return;

    const map = mapRef.current;
    if (!map) return;

    // 기존 오버레이 제거 - 중복 방지
    overlaysRef.current.forEach((o) => o.setMap(null));
    overlaysRef.current = [];

    // staions 존재 -> 첫 번째 좌표로 센터 이동
    stations.forEach((s) => {
      const pos = new window.kakao.maps.LatLng(s.lat, s.lng);
      const overlay = new window.kakao.maps.CustomOverlay({
        position: pos,
        yAnchor: 1,
        content: `
          <div class="stationMarker" title="${s.name ?? ""}">
            <div class="stationMarker__bubble">${Number(s.bikes ?? 0)}</div>
            <div class="stationMarker__bike">🚲</div>
          </div>
        `,
      });
      overlay.setMap(map);
      overlaysRef.current.push(overlay);
    });
  }, [mapReady, stations]);

  // 내 위치 찍기 - 나중에 추가

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {!sdkReady && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            zIndex: 10,
          }}
        >
          카카오맵 로딩 중...
        </div>
      )}
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
