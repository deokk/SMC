import { useEffect, useRef } from "react";
import useKakaoLoader from "../hooks/useKaKaoLoader.js";
import useRiderTracking from '../hooks/useRiderTracking';

// 🎨 디자인 상수 정의
const STYLES = {
  WALK: { color: "#888888", weight: 5, style: "solid", opacity: 1 },
  BUS: { color: "#3B6DC0", weight: 6, style: "solid", opacity: 1 },
  SUBWAY: { color: "#EF7C1C", weight: 6, style: "solid", opacity: 1 },
  BICYCLE: { color: "#008000", weight: 6, style: "solid", opacity: 0.8 },
  DEFAULT: { color: "#3277F6", weight: 6, style: "solid", opacity: 1 }
};

const SUBWAY_LINE_COLORS = {
  "1호선": "#0052A4", "2호선": "#00A84D", "3호선": "#EF7C1C", "4호선": "#00A5DE", 
  "5호선": "#996CAC", "6호선": "#CD7C2C", "7호선": "#747F00", "8호선": "#EA545D", 
  "9호선": "#BDB092", "수인분당선": "#F5A200", "신분당선": "#D31145", 
  "공항철도": "#7C8D93", "경의중앙선": "#77C4A3", "우이신설선": "#B0CE00", 
  "default": "#A1A1A1"
};

export default function KakaoMap({ stations, selectedRoute, isPredictionMode, predictionData, riderToTrack, myCurrentLocation, nearbyStations }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]); // 모든 대여소 마커 (일반 + 주변)
  const overlaysRef = useRef([]); // 모든 대여소 오버레이
  const polylinesRef = useRef([]);
  const startEndMarkersRef = useRef([]);
  const riderMarkerRef = useRef(null);
  const myLocationMarkerRef = useRef(null);
  const sdkReady = useKakaoLoader();

  const { riderLocation } = useRiderTracking(riderToTrack);

  const START_MARKER_IMAGE_SRC = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="12" fill="%23007BFF" stroke="%23FFFFFF" stroke-width="2"/><text x="15" y="19" font-family="Arial" font-size="10" fill="%23FFFFFF" text-anchor="middle" font-weight="bold">출발</text></svg>';
  const END_MARKER_IMAGE_SRC = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="12" fill="%23DC3545" stroke="%23FFFFFF" stroke-width="2"/><text x="15" y="19" font-family="Arial" font-size="10" fill="%23FFFFFF" text-anchor="middle" font-weight="bold">도착</text></svg>';
  const MY_LOCATION_MARKER_IMAGE_SRC = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20"><circle cx="10" cy="10" r="8" fill="%2300A8FF" stroke="%23FFFFFF" stroke-width="2"/></svg>';
  
  useEffect(() => {
    if (!sdkReady || !containerRef.current || mapRef.current) return;
    window.kakao.maps.load(() => {
      const center = new window.kakao.maps.LatLng(37.5408, 127.0793);
      mapRef.current = new window.kakao.maps.Map(containerRef.current, { center, level: 5, draggable: true });
    });
  }, [sdkReady]);

  // 대여소 마커 및 오버레이를 그리는 통합 useEffect
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !window.kakao || !stations) return;

    // 항상 기존 마커와 오버레이는 모두 지웁니다.
    markersRef.current.forEach((marker) => marker.setMap(null));
    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    markersRef.current = [];
    overlaysRef.current = [];

    // 어떤 대여소 목록을 그릴지 결정
    // 경로가 선택되면 '주변 대여소'만, 그렇지 않으면 '전체 대여소'를 그립니다.
    const stationsToDraw = selectedRoute ? nearbyStations : stations;

    if (!stationsToDraw) return;
    
    stationsToDraw.forEach((station) => {
      if (station.latitude == null || station.longitude == null) return;
      
      const markerPosition = new window.kakao.maps.LatLng(station.latitude, station.longitude);
      const marker = new window.kakao.maps.Marker({ position: markerPosition, title: station.station_name || station.station_display_name });
      marker.setMap(map);
      markersRef.current.push(marker);

      // 개수 오버레이는 항상 표시
      const count = isPredictionMode ? predictionData[station.station_id] ?? '?' : station.available_bikes;
      const content = document.createElement("div");
      content.className = isPredictionMode ? 'overlay-content prediction' : 'overlay-content';
      content.innerHTML = `${count}`;
    
      const customOverlay = new window.kakao.maps.CustomOverlay({
        map: map,
        position: markerPosition,
        content: content,
        yAnchor: 2.2,
        zIndex: 3,
      });
      overlaysRef.current.push(customOverlay);
    });

    // 경로가 없을 때만 전체 대여소를 기준으로 지도를 확대/축소
    if (stationsToDraw.length > 0 && !selectedRoute) {
      const bounds = new window.kakao.maps.LatLngBounds();
      stationsToDraw.forEach((station) => {
        if (station.latitude !== undefined && station.longitude !== undefined) {
           bounds.extend(new window.kakao.maps.LatLng(station.latitude, station.longitude));
        }
      });
      if (!bounds.isEmpty()) map.setBounds(bounds);
    }
  }, [stations, nearbyStations, selectedRoute, isPredictionMode, predictionData]);

  // 경로 폴리라인을 그리는 useEffect
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !window.kakao) return;

    polylinesRef.current.forEach(p => p.setMap(null));
    polylinesRef.current = [];
    startEndMarkersRef.current.forEach(m => m.setMap(null));
    startEndMarkersRef.current = [];

    if (selectedRoute && selectedRoute.steps && selectedRoute.steps.length > 0) {
      const bounds = new window.kakao.maps.LatLngBounds();
      
      selectedRoute.steps.forEach(step => {
        if (!step.polyline || step.polyline.length === 0) return;
        const path = step.polyline.map(coord => new window.kakao.maps.LatLng(coord[0], coord[1]));
        const style = STYLES[step.type] || STYLES.DEFAULT;
        let lineColor = style.color;
        if (step.type === 'SUBWAY') lineColor = SUBWAY_LINE_COLORS[step.name] || SUBWAY_LINE_COLORS.default;
        
        const mainPolyline = new window.kakao.maps.Polyline({
            path,
            strokeWeight: style.weight,
            strokeColor: lineColor,
            strokeOpacity: style.opacity,
            strokeStyle: style.style,
            zIndex: 2
        });
        mainPolyline.setMap(map);
        polylinesRef.current.push(mainPolyline);

        path.forEach(p => bounds.extend(p));
      });
     
      const firstStep = selectedRoute.steps.find(s => s.polyline && s.polyline.length > 0);
      const lastStep = selectedRoute.steps[selectedRoute.steps.length - 1];

      if (firstStep && lastStep?.polyline?.length > 0) {
        const startCoord = new window.kakao.maps.LatLng(firstStep.polyline[0][0], firstStep.polyline[0][1]);
        const endCoord = new window.kakao.maps.LatLng(lastStep.polyline[lastStep.polyline.length - 1][0], lastStep.polyline[lastStep.polyline.length - 1][1]);
        
        const startMarkerImg = new window.kakao.maps.MarkerImage(START_MARKER_IMAGE_SRC, new window.kakao.maps.Size(30, 30), { offset: new window.kakao.maps.Point(15, 30) });
        const endMarkerImg = new window.kakao.maps.MarkerImage(END_MARKER_IMAGE_SRC, new window.kakao.maps.Size(30, 30), { offset: new window.kakao.maps.Point(15, 30) });

        const startMarker = new window.kakao.maps.Marker({ position: startCoord, image: startMarkerImg, map, zIndex: 5 });
        const endMarker = new window.kakao.maps.Marker({ position: endCoord, image: endMarkerImg, map, zIndex: 5 });
        
        startEndMarkersRef.current.push(startMarker, endMarker);
        if (!bounds.isEmpty()) map.setBounds(bounds, 100, 50, 100, 50);
      }
    }
  }, [selectedRoute]);

  // 내 위치 마커
  useEffect(() => {
    if (!mapRef.current || !window.kakao) return;
    const map = mapRef.current;

    if (myCurrentLocation) {
      const myPosition = new window.kakao.maps.LatLng(myCurrentLocation.latitude, myCurrentLocation.longitude);
      const myLocationMarkerImage = new window.kakao.maps.MarkerImage(MY_LOCATION_MARKER_IMAGE_SRC, new window.kakao.maps.Size(20, 20), { offset: new window.kakao.maps.Point(10, 10) });
      
      if (!myLocationMarkerRef.current) {
        const marker = new window.kakao.maps.Marker({ position: myPosition, image: myLocationMarkerImage, map, zIndex: 4 });
        myLocationMarkerRef.current = marker;
      } else {
        myLocationMarkerRef.current.setPosition(myPosition);
        if (!myLocationMarkerRef.current.getMap()) {
          myLocationMarkerRef.current.setMap(map);
        }
      }
    } else {
      // 위치 정보가 없으면 마커를 제거
      if (myLocationMarkerRef.current) {
        myLocationMarkerRef.current.setMap(null);
      }
    }
  }, [myCurrentLocation]);

  // 라이더 추적 마커
  useEffect(() => {
    if (!mapRef.current || !window.kakao) return;
    const map = mapRef.current;
    
    if (riderLocation) {
      const riderPosition = new window.kakao.maps.LatLng(riderLocation.latitude, riderLocation.longitude);
      if (!riderMarkerRef.current) {
        const marker = new window.kakao.maps.Marker({ position: riderPosition, map, zIndex: 4 });
        riderMarkerRef.current = marker;
      } else {
        riderMarkerRef.current.setPosition(riderPosition);
        if (!riderMarkerRef.current.getMap()) { // 마커가 지도에 없으면 다시 추가
          riderMarkerRef.current.setMap(map);
        }
      }
    } else {
      // riderLocation이 없으면 마커를 제거
      if (riderMarkerRef.current) {
        riderMarkerRef.current.setMap(null);
      }
    }
  }, [riderLocation]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      {!sdkReady && <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>로딩 중...</div>}
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}