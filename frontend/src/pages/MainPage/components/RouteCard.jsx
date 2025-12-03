export default function RouteCard({ from, setFrom, to, setTo }) {
  return (
    <div className="mp-card mp-card--route">
      <div className="mp-routeCol" aria-hidden="true">
        <div className="mp-dot mp-dot--from">P</div>
        <div className="mp-routeLine" />
        <div className="mp-dot mp-dot--to" />
      </div>

      <div className="mp-fields">
        <div className="mp-row">
          <input
            className="mp-input"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            placeholder="출발지"
            aria-label="출발지"
          />
          <button className="mp-clear" onClick={() => setFrom("")} aria-label="출발지 지우기">
            ×
          </button>
        </div>
        <div className="mp-divider" />
        <div className="mp-row">
          <input
            className="mp-input"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="도착지"
            aria-label="도착지"
          />
          <button className="mp-clear" onClick={() => setTo("")} aria-label="도착지 지우기">
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
