import { useEffect, useMemo, useState } from "react";
import "./timepicker.css";

const pad2 = (n) => String(n).padStart(2, "0");

const isSameDay = (a, b) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

const addDays = (d, days) => {
  const nd = new Date(d);
  nd.setDate(nd.getDate() + days);
  return nd;
};

const dateLabelKR = (d) => {
  const today = new Date();
  const tomorrow = addDays(today, 1);
  if (isSameDay(d, today)) return "오늘";
  if (isSameDay(d, tomorrow)) return "내일";
  return `${d.getMonth() + 1}월 ${d.getDate()}일`;
};

export default function TimePickerModal({ open, initialValue, onClose, onConfirm }) {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [meridiem, setMeridiem] = useState("오후"); // "오전" | "오후"
  const [hour, setHour] = useState(12); // 1~12
  const [minute, setMinute] = useState(0); // 0~59

  const hourOptions = useMemo(() => Array.from({ length: 12 }, (_, i) => i + 1), []);
  const minuteOptions = useMemo(() => Array.from({ length: 6 }, (_, i) => i * 10), []); // 00,10,...50

  const dateChips = useMemo(() => {
    const base = new Date();
    return [
      { key: "today", date: new Date(base), label: "오늘" },
      { key: "tomorrow", date: addDays(base, 1), label: "내일" },
      { key: "d2", date: addDays(base, 2), label: `${addDays(base, 2).getMonth() + 1}월 ${addDays(base, 2).getDate()}일` },
      { key: "d3", date: addDays(base, 3), label: `${addDays(base, 3).getMonth() + 1}월 ${addDays(base, 3).getDate()}일` },
      { key: "d4", date: addDays(base, 4), label: `${addDays(base, 4).getMonth() + 1}월 ${addDays(base, 4).getDate()}일` },
    ];
  }, []);

  useEffect(() => {
    if (!open) return;
    const v = initialValue;
    if (!v) {
      const now = new Date();
      setSelectedDate(now);
      setMeridiem(now.getHours() < 12 ? "오전" : "오후");
      const hr12 = now.getHours() % 12 || 12;
      setHour(hr12);
      setMinute(Math.floor(now.getMinutes() / 10) * 10);
      return;
    }
    setSelectedDate(v.date);
    setMeridiem(v.meridiem);
    setHour(v.hour);
    setMinute(Math.floor(v.minute / 10) * 10);
  }, [open, initialValue]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const selectedLabel = dateLabelKR(selectedDate);

  const handleConfirm = () => {
    onConfirm({
      date: selectedDate,
      meridiem,
      hour,
      minute,
      text: `${selectedLabel} ${meridiem} ${pad2(hour)}:${pad2(minute)}`,
    });
  };

  return (
    <div className="tp-overlay" role="dialog" aria-modal="true" aria-label="출발 시각 설정">
      <button className="tp-backdrop" onClick={onClose} aria-label="닫기 배경" />

      <div className="tp-sheet">
        <div className="tp-title">출발 시각 설정</div>

        <div className="tp-chipRow" role="tablist" aria-label="출발 날짜 선택">
          {dateChips.map((c) => {
            const active = isSameDay(c.date, selectedDate);
            return (
              <button
                key={c.key}
                className={`tp-chip ${active ? "is-active" : ""}`}
                type="button"
                onClick={() => setSelectedDate(c.date)}
              >
                {c.label}
              </button>
            );
          })}
        </div>

        <div className="tp-picker">
          <div className="tp-wheel" aria-label="시간 선택">
            {hourOptions.map((h) => {
              const active = h === hour;
              return (
                <button
                  key={h}
                  type="button"
                  className={`tp-wheelItem ${active ? "is-active" : ""}`}
                  onClick={() => setHour(h)}
                >
                  {pad2(h)}
                </button>
              );
            })}
          </div>

          <div className="tp-colon" aria-hidden="true">
            :
          </div>

          <div className="tp-wheel" aria-label="분 선택">
            {minuteOptions.map((m) => {
              const active = m === minute;
              return (
                <button
                  key={m}
                  type="button"
                  className={`tp-wheelItem ${active ? "is-active" : ""}`}
                  onClick={() => setMinute(m)}
                >
                  {pad2(m)}
                </button>
              );
            })}
          </div>
        </div>

        <div className="tp-ampm" aria-label="오전/오후 선택">
          <button
            type="button"
            className={`tp-ampmBtn ${meridiem === "오전" ? "is-active" : ""}`}
            onClick={() => setMeridiem("오전")}
          >
            오전
          </button>
          <button
            type="button"
            className={`tp-ampmBtn ${meridiem === "오후" ? "is-active" : ""}`}
            onClick={() => setMeridiem("오후")}
          >
            오후
          </button>
        </div>

        <div className="tp-actions">
          <button type="button" className="tp-actionBtn tp-set" onClick={handleConfirm}>
            설정
          </button>
          <button type="button" className="tp-actionBtn tp-close" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
