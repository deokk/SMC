import { useMemo, useState, useEffect, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import KaKaoMap from "../../components/KaKaoMap";
import Header from "./components/Header";
import RouteCard from "./components/RouteCard";
import TimeCard from "./components/TimeCard";
import TimePickerModal from "./components/TimePickerModal";
import RouteResult from "./components/RouteResult";
import RouteDetailPanel from "./components/RouteDetailPanel";
import SideMenu from "../../components/SideMenu";
import useMediaQuery from "../../hooks/useMediaQuery";
import "./MainPage.css";

const formatCurrentTime = () => {
  const now = new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const meridiem = hour < 12 ? "오전" : "오후";
  const hour12 = hour % 12 || 12;
  const dateLabel = "오늘";
  return `${dateLabel} ${meridiem} ${String(hour12).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
};

const addDays = (d, days) => {
  const nd = new Date(d);
  nd.setDate(nd.getDate() + days);
  return nd;
};

const parseTimeText = (timeText) => {
  try {
    const today = new Date();
    const parts = timeText.trim().split(/\s+/);

    if (parts.length < 3) return null;

    const datePart = parts[0];
    const meridiem = parts[1] === "오전" ? "오전" : "오후";
    const [hhStr, mmStr] = parts[2].split(":");
    if (!hhStr || !mmStr) return null;

    const hour = Math.min(12, Math.max(1, Number(hhStr)));
    const minute = Math.min(59, Math.max(0, Number(mmStr)));

    let date = new Date(today);
    if (datePart === "오늘") {
      date = new Date(today);
    } else if (datePart === "내일") {
      date = addDays(today, 1);
    } else {
      if (datePart.includes("월") && datePart.includes("일")) {
        const m = Number(datePart.split("월")[0]);
        const dd = Number(datePart.split("월")[1].replace("일", "").trim());
        const guessed = new Date(today.getFullYear(), m - 1, dd);
        date = guessed;
      } else {
        return null;
      }
    }

    return { date, meridiem, hour, minute };
  } catch {
    return null;
  }
};

const buildDateFromValue = (value) => {
  if (!value || !value.date) return null;
  const { date, meridiem, hour, minute } = value;
  const result = new Date(date);
  const hour24 = meridiem === "오전" ? (hour === 12 ? 0 : hour) : (hour === 12 ? 12 : hour + 12);
  result.setHours(hour24, minute, 0, 0);
  return result;
};

export default function MainPage() {
  const {
    from,
    setFrom,
    to,
    setTo,
    routes,
    setRoutes,
    isRoutesOpen,
    setIsRoutesOpen,
    selectedRoute,
    setSelectedRoute,
  } = useOutletContext();
  
  const isMobile = useMediaQuery('(max-width: 768px)'); // 화면 크기 감지

  const [timeText, setTimeText] = useState(formatCurrentTime());
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [stations, setStations] = useState([]);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [isPredictionMode, setIsPredictionMode] = useState(false);
  const [predictionData, setPredictionData] = useState({});
  const [isPredicting, setIsPredicting] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/stations/realtime')
      .then(res => res.json())
      .then(setStations)
      .catch(err => console.error("Failed to fetch real-time stations:", err));
  }, []);

  const handleSearch = async () => {
    if (!window.kakao || !window.kakao.maps || !window.kakao.maps.services || !window.kakao.maps.services.Geocoder) {
      alert("지도 서비스(주소 검색)가 로드되지 않았습니다. 잠시 후 다시 시도해주세요.");
      return;
    }
    const getCoords = (address) => {
      return new Promise((resolve, reject) => {
        const places = new window.kakao.maps.services.Places();
        places.keywordSearch(address, (result, status) => {
          if (status === window.kakao.maps.services.Status.OK) {
            resolve({ lat: result[0].y, lon: result[0].x });
          } else {
            const geocoder = new window.kakao.maps.services.Geocoder();
            geocoder.addressSearch(address, (geoResult, geoStatus) => {
              if (geoStatus === window.kakao.maps.services.Status.OK) {
                resolve({ lat: geoResult[0].y, lon: geoResult[0].x });
              } else {
                reject(new Error("주소/장소 검색 실패: " + address));
              }
            });
          }
        });
      });
    };
    try {
      const startCoords = await getCoords(from);
      const endCoords = await getCoords(to);
      const response = await fetch("http://127.0.0.1:8000/route/optimized", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_lat: parseFloat(startCoords.lat), start_lon: parseFloat(startCoords.lon),
          end_lat: parseFloat(endCoords.lat), end_lon: parseFloat(endCoords.lon),
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "경로 탐색 API 서버에 문제가 발생했습니다.");
      }
      const routeData = await response.json();
      setRoutes(routeData);
      setIsRoutesOpen(true);
      setSelectedRoute(null);
    } catch (error) {
      console.error("경로 검색 실패:", error);
      alert(error.message || "경로 검색 중 오류가 발생했습니다.");
    }
  };

  const handleRouteSelect = (route) => {
    if (selectedRoute && selectedRoute === route) {
      setSelectedRoute(null);
    } else {
      setSelectedRoute(route);
    }
  };

  const handleTimeConfirm = useCallback(async (value) => {
    setTimeText(value.text);
    closeTimeModal();
    const selectedDate = buildDateFromValue(value);
    if (!selectedDate) return;

    const diffMinutes = Math.round((selectedDate - new Date()) / 60000);

    if (diffMinutes < 5) {
      setIsPredictionMode(false);
      setPredictionData({});
      return;
    }

    setIsPredicting(true);
    setIsPredictionMode(true);
    try {
      const results = await Promise.all(stations.map(station =>
        fetch(`http://localhost:8000/predict/hybrid/${station.station_id}?n_minutes=${diffMinutes}`)
          .then(res => res.json())
          .catch(() => null)
      ));
      const newPredictionData = results.filter(Boolean).reduce((acc, res) => {
        acc[res.station_id] = res.predicted_bike_count;
        return acc;
      }, {});
      setPredictionData(newPredictionData);
    } catch (error) {
      console.error("Prediction fetch error:", error);
      setIsPredictionMode(false);
    } finally {
      setIsPredicting(false);
    }
  }, [stations]);

  const openTimeModal = () => setIsTimeOpen(true);
  const closeTimeModal = () => setIsTimeOpen(false);
  const openSideMenu = () => setIsSideMenuOpen(true);
  const closeSideMenu = () => setIsSideMenuOpen(false);
  const initialTimeValue = useMemo(() => parseTimeText(timeText), [timeText]);

  return (
    <div className="mp-root">
      <div className="mp-top">
        <Header />
        
        {/* 모바일이고 경로 선택 시, 상세 패널을 여기에 렌더링 */}
        {isMobile && selectedRoute && (
          <div className="mp-detail-panel-container">
            <RouteDetailPanel route={selectedRoute} onBack={() => setSelectedRoute(null)} />
          </div>
        )}
        
        {/* 데스크탑이거나, 모바일에서 경로 미선택 시, 검색 카드 렌더링 */}
        {(!isMobile || !selectedRoute) && (
          <section className="mp-cards">
            <RouteCard from={from} setFrom={setFrom} to={to} setTo={setTo} />
            <TimeCard timeText={timeText} setTimeText={setTimeText} openTimeModal={openTimeModal} />
          </section>
        )}
      </div>

      <main className="mp-map" aria-label="map area">
        <div className="mp-mapContainer">
          <KaKaoMap 
            stations={stations} 
            selectedRoute={selectedRoute}
            isPredictionMode={isPredictionMode}
            predictionData={predictionData}
          />

          {isRoutesOpen && (
            // 모바일에서는 경로가 선택되면 오버레이를 숨김 (상세 정보가 상단에 있으므로)
            (!isMobile || !selectedRoute) && (
              <div className="mp-routeOverlay">
                {/* 데스크탑에서는 상세 정보와 목록 전환 */}
                {!isMobile && selectedRoute ? (
                  <RouteDetailPanel
                    route={selectedRoute}
                    onBack={() => setSelectedRoute(null)}
                  />
                ) : (
                  <RouteResult
                    routes={routes}
                    selectedRoute={selectedRoute}
                    isOpen={isRoutesOpen}
                    onBack={() => {
                      setIsRoutesOpen(false);
                      setSelectedRoute(null);
                    }}
                    onRouteSelect={handleRouteSelect}
                  />
                )}
              </div>
            )
          )}
        </div>
      </main>

      {isPredicting && <div className="mp-loading-overlay">예측 중...</div>}
      <nav className="mp-bottom">
        <button
          className="mp-iconBtn"
          type="button"
          aria-label="메뉴"
          onClick={openSideMenu}
        >
          <img src="/list.svg" alt="메뉴" width="23" height="15" />
        </button>
        <button className="mp-cta" onClick={handleSearch}>길찾기</button>
        <button className="mp-iconBtn">P</button>
      </nav>

      <SideMenu
        isOpen={isSideMenuOpen}
        onClose={closeSideMenu}
      />
      <TimePickerModal
        open={isTimeOpen}
        initialValue={initialTimeValue}
        onClose={closeTimeModal}
        onConfirm={handleTimeConfirm}
      />
    </div>
  );
}
