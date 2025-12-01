import { useMemo, useState } from "react";
import KaKaoMap from "../../components/KaKaoMap";
import Header from "./components/Header";
import RouteCard from "./components/RouteCard";
import TimeCard from "./components/TimeCard";
import TimePickerModal from "./components/TimePickerModal";
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
        <div className="mp-mapInner">
          <KaKaoMap />
        </div>
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
