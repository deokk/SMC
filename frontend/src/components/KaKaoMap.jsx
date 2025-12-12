import { useEffect, useRef } from "react";

import useKakaoLoader from "../hooks/useKaKaoLoader.js";



// 🎨 디자인 상수 정의

const STYLES = {

  WALK: {

    color: "#888888",

    weight: 5,

    style: "solid", // "dot"에서 "dash"로 변경하여 가시성 확보

    opacity: 1,

  },

  BUS: {

    color: "#3B6DC0", // 간선버스 파란색

    weight: 6,

    style: "solid",

    opacity: 1,

  },

  SUBWAY: {

    color: "#EF7C1C", // 기본 오렌지 (아래에서 호선별 색상으로 덮어씀)

    weight: 6,

    style: "solid",

    opacity: 1,

  },

  DEFAULT: {

    color: "#3277F6",

    weight: 6,

    style: "solid",

    opacity: 1,

  }

};



const SUBWAY_LINE_COLORS = {

  "1호선": "#0052A4",

  "2호선": "#00A84D",

  "3호선": "#EF7C1C",

  "4호선": "#00A5DE",

  "5호선": "#996CAC",

  "6호선": "#CD7C2C",

  "7호선": "#747F00",

  "8호선": "#EA545D",

  "9호선": "#BDB092",

  "수인분당선": "#F5A200",

  "신분당선": "#D31145",

  "공항철도": "#7C8D93",

  "경의중앙선": "#77C4A3",

  "우이신설선": "#B0CE00",

  "default": "#EF7C1C", // 기본값

};



export default function KakaoMap({ stations, selectedRoute, isPredictionMode, predictionData }) {

  const containerRef = useRef(null);

  const mapRef = useRef(null);

  const markersRef = useRef([]);

  const overlaysRef = useRef([]);

  const polylinesRef = useRef([]);

  const startEndMarkersRef = useRef([]); // 출발/도착 마커를 관리할 ref 추가

  const sdkReady = useKakaoLoader();



  // 커스텀 마커 이미지

  const START_MARKER_IMAGE_SRC = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="12" fill="%23007BFF" stroke="%23FFFFFF" stroke-width="2"/><text x="15" y="19" font-family="Arial" font-size="10" fill="%23FFFFFF" text-anchor="middle" font-weight="bold">출발</text></svg>';

  const END_MARKER_IMAGE_SRC = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="12" fill="%23DC3545" stroke="%23FFFFFF" stroke-width="2"/><text x="15" y="19" font-family="Arial" font-size="10" fill="%23FFFFFF" text-anchor="middle" font-weight="bold">도착</text></svg>';



        // 1. 지도 생성 (타이밍 문제 해결)



        useEffect(() => {



          if (!sdkReady || !containerRef.current || mapRef.current) return;



          



          // kakao.maps.load는 스크립트가 로드되고 모든 API를 사용할 수 있을 때 콜백을 실행하므로,



          // 타이밍 이슈를 해결할 수 있는 가장 안정적인 방법입니다.



          window.kakao.maps.load(() => {



            const center = new window.kakao.maps.LatLng(37.5408, 127.0793);



                        mapRef.current = new window.kakao.maps.Map(containerRef.current, { 



                          center, 



                          level: 5,



                          draggable: true // 드래그 기능 강제 활성화



                        });



                      });



                    }, [sdkReady]); // sdkReady가 true가 되면 이 효과를 실행합니다.



  // 2. 마커 및 오버레이 업데이트 (변경 없음)

  useEffect(() => {

    const map = mapRef.current;

    if (!map || !stations) return;



    markersRef.current.forEach((marker) => marker.setMap(null));

    overlaysRef.current.forEach((overlay) => overlay.setMap(null));

    markersRef.current = [];

    overlaysRef.current = [];



    stations.forEach((station) => {

      if (station.latitude === undefined || station.longitude === undefined) return;

      const markerPosition = new window.kakao.maps.LatLng(station.latitude, station.longitude);

     

      const marker = new window.kakao.maps.Marker({ position: markerPosition, title: station.station_display_name });

      marker.setMap(map);

      markersRef.current.push(marker);



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



    if (stations.length > 0 && !selectedRoute) {

      const bounds = new window.kakao.maps.LatLngBounds();

      stations.forEach((station) => {

        if (station.latitude !== undefined && station.longitude !== undefined) {

           bounds.extend(new window.kakao.maps.LatLng(station.latitude, station.longitude));

        }

      });

      if (!bounds.isEmpty()) map.setBounds(bounds);

    }

  }, [stations, selectedRoute, isPredictionMode, predictionData]);





  // 3. 경로선 및 출발/도착 마커 그리기

  useEffect(() => {

    const map = mapRef.current;

    if (!map) return;



    // 기존 폴리라인 및 마커 제거

    polylinesRef.current.forEach(p => p.setMap(null));

    polylinesRef.current = [];

    startEndMarkersRef.current.forEach(m => m.setMap(null));

    startEndMarkersRef.current = [];



    if (selectedRoute && selectedRoute.steps && selectedRoute.steps.length > 0) {

      const bounds = new window.kakao.maps.LatLngBounds();

      let hasValidPolyline = false; // 경로선이 하나라도 그려졌는지 확인



      selectedRoute.steps.forEach(step => {

        if (!step.polyline || step.polyline.length === 0) return;

        hasValidPolyline = true;



        const path = step.polyline.map(coord => new window.kakao.maps.LatLng(coord[0], coord[1]));

        const style = STYLES[step.type] || STYLES.DEFAULT;

        let lineColor = style.color;



        if (step.type === 'SUBWAY') {

            lineColor = SUBWAY_LINE_COLORS[step.name] || SUBWAY_LINE_COLORS.default;

        }

       

        const borderPolyline = new window.kakao.maps.Polyline({

          path: path,

          strokeWeight: style.weight + 4,

          strokeColor: '#FFFFFF',

          strokeOpacity: 1,

          strokeStyle: 'solid',

          strokeLineCap: 'round',

          strokeLineJoin: 'round',

          zIndex: 1

        });

        borderPolyline.setMap(map);

        polylinesRef.current.push(borderPolyline);

       

        const mainPolyline = new window.kakao.maps.Polyline({

            path: path,

            strokeWeight: style.weight,

            strokeColor: lineColor,

            strokeOpacity: style.opacity,

            strokeStyle: style.style,

            strokeLineCap: 'round',

            strokeLineJoin: 'round',

            zIndex: 2

        });

        mainPolyline.setMap(map);

        polylinesRef.current.push(mainPolyline);



        path.forEach(point => bounds.extend(point));

      });

     

      if (hasValidPolyline) {

          // 전체 출발/도착 좌표 추출

          const firstStep = selectedRoute.steps.find(s => s.polyline && s.polyline.length > 0);

          const allSteps = selectedRoute.steps.filter(s => s.polyline && s.polyline.length > 0);

          const lastStep = allSteps[allSteps.length - 1];



          // 모든 step.polyline이 비어있는 경우를 대비

          if (firstStep && lastStep) {

            const overallStartCoord = new window.kakao.maps.LatLng(firstStep.polyline[0][0], firstStep.polyline[0][1]);

            const overallEndCoord = new window.kakao.maps.LatLng(lastStep.polyline[lastStep.polyline.length - 1][0], lastStep.polyline[lastStep.polyline.length - 1][1]);



            // 커스텀 마커 이미지 생성

            const startMarkerImage = new window.kakao.maps.MarkerImage(START_MARKER_IMAGE_SRC, new window.kakao.maps.Size(30, 30), { offset: new window.kakao.maps.Point(15, 30) });

            const endMarkerImage = new window.kakao.maps.MarkerImage(END_MARKER_IMAGE_SRC, new window.kakao.maps.Size(30, 30), { offset: new window.kakao.maps.Point(15, 30) });



            // 출발 마커 생성

            const startMarker = new window.kakao.maps.Marker({

                position: overallStartCoord,

                image: startMarkerImage,

                map: map,

                zIndex: 3

            });

            startEndMarkersRef.current.push(startMarker);



            // 도착 마커 생성

            const endMarker = new window.kakao.maps.Marker({

                position: overallEndCoord,

                image: endMarkerImage,

                map: map,

                zIndex: 3

            });

            startEndMarkersRef.current.push(endMarker);



            // 마커와 경로선이 화면에 꽉 차도록 줌 레벨 조정 (여백 추가)

            if (!bounds.isEmpty()) {

                bounds.extend(overallStartCoord);

                bounds.extend(overallEndCoord);

                map.setBounds(bounds, 100, 50, 100, 50);

            }

          }

      }

    }

  }, [selectedRoute]);



  return (

    <div style={{ width: "100%", height: "100%" }}>

      {!sdkReady && <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>로딩 중...</div>}

      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />

    </div>

  );

}