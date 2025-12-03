import { useMemo, useState } from "react";
import KaKaoMap from "../../components/KakaoMap";
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
    const parts = timeText.trim().split(/\s+/);

    if (parts.length < 3) return null;

    const datePart = parts[0];
    const meridiem = parts[1] === "午前" ? "午前" : "午後";
    const [hhStr, mmStr] = parts[2].split(":");
    if (!hhStr || !mmStr) return null;

    const hour = Math.min(12, Math.max(1, Number(hhStr)));
    const minute = Math.min(59, Math.max(0, Number(mmStr)));

    let date = new Date(today);
    if (datePart === "今日") {
      date = new Date(today);
    } else if (datePart === "明日") {
      date = addDays(today, 1);
    } else {
      if (datePart.includes("月") && datePart.includes("日")) {
        const m = Number(datePart.split("月")[0]);
        const dd = Number(datePart.split("月")[1].replace("日", "").trim());
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

export default function MainPage() {
  const [from, setFrom] = useState("건국대학교 서울캠퍼스");
  const [to, setTo] = useState("화양동 주민센터");
  const [timeText, setTimeText] = useState("오늘 오후 12:00");
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [routes, setRoutes] = useState(null);
  const [isRoutesOpen, setIsRoutesOpen] = useState(false);

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
        <button className="mp-iconBtn" type="button" aria-label="메뉴">
          P
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
