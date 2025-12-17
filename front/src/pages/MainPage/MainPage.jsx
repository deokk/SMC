import { useMemo, useState } from "react";
import KaKaoMap from "../../components/KakaoMap";
import SideMenu from "../../components/SideMenu";
import { mockStations } from "../../mocks/stationMarkers";
import Header from "./components/Header";
import RouteCard from "./components/RouteCard";
import TimeCard from "./components/TimeCard";
import TimePickerModal from "./components/TimePickerModal";
import RouteResult from "./components/RouteResult";
import "./MainPage.css";

const addDays = (d, days) => {
  const nd = new Date(d);
  nd.setDate(nd.getDate() + days);
  return nd;
};

const parseTimeText = (timeText) => {
  try {
    const today = new Date();
    const text = (timeText ?? "").trim();
    if (!text) return null;

    // 허용 포맷:
    // "오늘 오후 12:00"
    // "내일 오전 9:10"
    // "12월 4일 오후 3:20"
    const m = text.match(
      /^(오늘|내일|(\d{1,2})월\s*(\d{1,2})일)\s+(오전|오후)\s+(\d{1,2}):(\d{1,2})$/
    );
    if (!m) return null;

    const dateToken = m[1];
    const monthStr = m[2];
    const dayStr = m[3];
    const meridiem = m[4];
    const hhStr = m[5];
    const mmStr = m[6];

    let date = new Date(today);
    if (dateToken === "오늘") {
      date = new Date(today);
    } else if (dateToken === "내일") {
      date = new Date(today);
      date.setDate(date.getDate() + 1);
    } else {
      const month = Number(monthStr);
      const day = Number(dayStr);
      if (!Number.isFinite(month) || !Number.isFinite(day)) return null;
      date = new Date(today.getFullYear(), month - 1, day);
    }

    const hour = Math.min(12, Math.max(1, Number(hhStr)));
    const minute = Math.min(59, Math.max(0, Number(mmStr)));

    return { date, meridiem, hour, minute };
  } catch {
    return null;
  }
};

export default function MainPage() {
  const [from, setFrom] = useState("건국대학교 서울캠퍼스");
  const [to, setTo] = useState("화양동 주민센터");
  const [timeText, setTimeText] = useState("오늘 오후 12:00");
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [routes, setRoutes] = useState(null);
  const [isRoutesOpen, setIsRoutesOpen] = useState(false);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [startCoords, setStartCoords] = useState(null); // { lat: 37.xxx, lng: 127.xxx }
  const [endCoords, setEndCoords] = useState(null); // { lat: 37.xxx, lng: 127.xxx }

  const canSubmit = useMemo(() => {
    return (
      from.trim().length > 0 &&
      to.trim().length > 0 &&
      timeText.trim().length > 0
    );
  }, [from, to, timeText]);

  const openTimeModal = () => setIsTimeOpen(true);
  const closeTimeModal = () => setIsTimeOpen(false);

  const initialTimeValue = useMemo(() => parseTimeText(timeText), [timeText]);

  // 경로 검색
  const handleSearch = async () => {
    if (!window.kakao?.maps) return;

    try {
      // 실제로는 from/to 주소로 좌표를 검색해야 함
      // 여기서는 시뮬레이션으로 시간 데이터를 설정
      const mockRoutes = {
        transit: 45, // 분
        walking: 28,
        bike: 18,
      };

      setRoutes(mockRoutes);
      setIsRoutesOpen(true);
    } catch (error) {
      console.error("경로 검색 실패:", error);
    }
  };

  return (
    <div className="mp-root">
      <div className="mp-top">
        <Header />
        <section className="mp-cards" aria-label="route inputs">
          <RouteCard from={from} setFrom={setFrom} to={to} setTo={setTo} />
          <TimeCard
            timeText={timeText}
            setTimeText={setTimeText}
            openTimeModal={openTimeModal}
          />
        </section>
      </div>

      <main className="mp-map" aria-label="map area">
        {!isRoutesOpen && (
          <div className="mp-mapInner">
            <KaKaoMap stations={mockStations} />
          </div>
        )}
        {isRoutesOpen && (
          <RouteResult
            routes={routes}
            isOpen={isRoutesOpen}
            onBack={() => setIsRoutesOpen(false)}
          />
        )}
      </main>

      <nav className="mp-bottom" aria-label="bottom navigation">
        <button
          className="mp-iconBtn"
          type="button"
          aria-label="메뉴"
          onClick={() => setIsSideMenuOpen(true)}
        >
          <img src="/list.svg" alt="메뉴" width="23" height="15" />
        </button>

        <button
          className="mp-cta"
          type="button"
          disabled={!canSubmit}
          aria-disabled={!canSubmit}
          onClick={handleSearch}
        >
          예측 및 길찾기
        </button>

        <button className="mp-iconBtn" type="button" aria-label="문서">
          P
        </button>
      </nav>

      <SideMenu
        isOpen={isSideMenuOpen}
        onClose={() => setIsSideMenuOpen(false)}
      />

      <TimePickerModal
        open={isTimeOpen}
        initialValue={initialTimeValue}
        onClose={closeTimeModal}
        onConfirm={(v) => {
          setTimeText(v.text);
          closeTimeModal();
        }}
      />
    </div>
  );
}
