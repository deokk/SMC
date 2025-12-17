export default function TimeCard({ timeText, setTimeText, openTimeModal }) {
  return (
    <div className="mp-card mp-card--time">
      <img src="/time.svg" alt="시간" className="mp-timeIcon" />

      <div className="mp-row mp-row--time">
        {/* ✅ 클릭 시 모달만 열리도록 readOnly */}
        <input
          className="mp-input mp-input--time mp-input--clickable"
          value={timeText}
          readOnly
          onClick={openTimeModal}
          onFocus={(e) => e.target.blur()}
          placeholder="시간"
          aria-label="출발 시간"
        />
        <button
          className="mp-clear"
          onClick={() => setTimeText("")}
          aria-label="시간 지우기"
        >
          ×
        </button>
      </div>
    </div>
  );
}
