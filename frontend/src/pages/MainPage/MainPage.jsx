import { useMemo, useState, useEffect } from "react";
import KaKaoMap from "../../components/KaKaoMap";
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
  //期待フォーマット：
  // "今日午後12:00"
  // "明日午前09:10"
  // "12月17日午後02:20"
  try {
    const today = new Date();
    const parts = timeText.trim().split(/\s+/); // [日付ラベル, 午前/午後, hh:mm]

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
  
  // 기능 병합: 경로 검색 결과 상태 추가
  const [routes, setRoutes] = useState(null);
  const [isRoutesOpen, setIsRoutesOpen] = useState(false);

  // 기존 실시간 대여소 데이터 상태 유지
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 기존 실시간 대여소 데이터 API 호출 유지
  useEffect(() => {
    const fetchStations = async () => {
      try {
        const response = await fetch('http://localhost:8000/stations/realtime');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setStations(data);
      } catch (err) {
        setError(err);
        console.error("Failed to fetch real-time stations:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStations();
  }, []);

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

  // 기능 병합: front의 경로 검색 핸들러 추가
  const handleSearch = async () => {
    // 테스트를 위해 특정 대여소 ID와 예측 시간을 하드코딩합니다.
    const stationId = "ST-419"; // 예: 419번 대여소
    const minutesToPredict = 30; // 예: 30분 후

    try {
      const response = await fetch(
        `http://localhost:8000/stations/${stationId}/predict?n_minutes=${minutesToPredict}`
      );
      if (!response.ok) {
        throw new Error(`[API Error] Status: ${response.status}`);
      }
      const predictionResult = await response.json();
      
      // API 응답 결과를 routes 상태에 저장
      setRoutes(predictionResult);
      setIsRoutesOpen(true);
    } catch (error) {
      console.error("Prediction API fetch failed:", error);
      // 사용자에게 에러를 알리는 UI를 추가할 수 있습니다.
      alert("예측 데이터를 가져오는 데 실패했습니다.");
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
        {/* 기능 병합: isRoutesOpen 상태에 따라 조건부 렌더링 */}
        {!isRoutesOpen && (
          <div className="mp-mapInner">
            {/* 기존 stations 상태를 KaKaoMap에 전달 */}
            <KaKaoMap stations={stations} />
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
          // 기능 병합: onClick 이벤트 핸들러 연결
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
