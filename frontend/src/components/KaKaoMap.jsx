import { useEffect, useRef } from "react";
import useKakaoLoader from "../hooks/useKaKaoLoader.js";

export default function KakaoMap({ stations }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const overlaysRef = useRef([]);
  const sdkReady = useKakaoLoader();

  // 1. 지도 생성 (최초 한 번만 실행)
  useEffect(() => {
    if (!sdkReady || !containerRef.current) return;
    
    // window.kakao.maps.load를 사용하여 SDK가 완전히 로드된 후 지도 생성
    window.kakao.maps.load(() => {
      if (mapRef.current) return; // 이미 지도가 생성되었다면 중복 실행 방지

      const center = new window.kakao.maps.LatLng(37.5408, 127.0793);
      const map = new window.kakao.maps.Map(containerRef.current, {
        center,
        level: 5,
      });
      mapRef.current = map;
    });
  }, [sdkReady]);

  // 2. stations 데이터가 변경될 때마다 마커/오버레이 업데이트
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !stations) return;

    // 기존 마커와 오버레이 제거
    markersRef.current.forEach((marker) => marker.setMap(null));
    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    markersRef.current = [];
    overlaysRef.current = [];

    stations.forEach((station) => {
      if (station.latitude === undefined || station.longitude === undefined) return;

      const markerPosition = new window.kakao.maps.LatLng(
        station.latitude,
        station.longitude
      );

      const marker = new window.kakao.maps.Marker({
        position: markerPosition,
        title: station.station_display_name,
      });
      marker.setMap(map);
      markersRef.current.push(marker);

      const content = document.createElement("div");
      content.style.cssText = `
        background-color: white;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 3px 5px;
        font-size: 12px;
        font-weight: bold;
        color: #333;
        text-align: center;
        white-space: nowrap;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
      `;
      content.innerHTML = `${station.available_bikes}`;

      const customOverlay = new window.kakao.maps.CustomOverlay({
        map: map,
        position: markerPosition,
        content: content,
        yAnchor: 1.5,
        zIndex: 3,
      });
      overlaysRef.current.push(customOverlay);

      window.kakao.maps.event.addListener(marker, "click", function () {
        console.log(`클릭된 대여소: ${station.station_display_name}, ${station.available_bikes}대`);
      });
    });

    // 데이터가 있을 경우에만 지도 범위 조정
    if (stations.length > 0) {
      const bounds = new window.kakao.maps.LatLngBounds();
      stations.forEach((station) => {
        if (station.latitude !== undefined && station.longitude !== undefined) {
           bounds.extend(
            new window.kakao.maps.LatLng(station.latitude, station.longitude)
          );
        }
      });
      if (!bounds.isEmpty()) {
        map.setBounds(bounds);
      }
    }
  }, [stations]); // stations가 변경될 때만 이 effect를 실행

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
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
