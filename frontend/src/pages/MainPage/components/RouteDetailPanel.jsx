import "./RouteDetailPanel.css";

const formatTime = (minutes) => {
  if (minutes < 60) return `${minutes}분`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}시간 ${mins}분` : `${hours}시간`;
};

const getTransportStyle = (type, name = '') => {
  const SUBWAY_LINE_COLORS = {
    "1호선": "#0052A4", "2호선": "#00A84D", "3호선": "#EF7C1C", "4호선": "#00A5DE", 
    "5호선": "#996CAC", "6호선": "#CD7C2C", "7호선": "#747F00", "8호선": "#EA545D", 
    "9호선": "#BDB092", "수인분당선": "#F5A200", "신분당선": "#D31145", 
    "공항철도": "#7C8D93", "경의중앙선": "#77C4A3", "우이신설선": "#B0CE00", 
    "default": "#A1A1A1"
  };

  const t = type.toUpperCase();
  if (t === "SUBWAY") {
    const color = SUBWAY_LINE_COLORS[name] || SUBWAY_LINE_COLORS.default;
    return { color, bg: `${color}20`, icon: "🚇" };
  }
  if (t === "BUS") return { color: "#3b6dc0", bg: "#eef4ff", icon: "🚌" };
  if (t === "WALK") return { color: "#888", bg: "#f5f5f5", icon: "🚶" };
  if (t === "BIKE") return { color: "#007bff", bg: "#e6f2ff", icon: "🚴" };
  return { color: "#333", bg: "#eee", icon: "📍" };
};


export default function RouteDetailPanel({ route, onBack }) {
  if (!route) return null;

  return (
    <div className="rdp-container">
      <div className="rdp-header">
        <button className="rdp-backBtn" onClick={onBack}>
          ← 목록
        </button>
        <h2 className="rdp-title">상세 경로</h2>
      </div>

      <div className="rdp-summary">
        <p><strong>총 소요 시간:</strong> {formatTime(route.duration)}</p>
        <p><strong>총 요금:</strong> {route.fare?.toLocaleString()}원</p>
        <p><strong>도보 시간:</strong> {formatTime(route.steps.filter(s=>s.type==='WALK').reduce((sum,s)=>sum+s.duration,0))}</p>
      </div>

      <div className="rdp-steps-wrapper">
        <div className="rdp-steps">
          {route.steps.map((step, index) => {
            const style = getTransportStyle(step.type, step.name);
            return (
              <div key={index} className="rdp-step-card">
                <div className="rdp-step-icon" style={{ backgroundColor: style.bg, color: style.color }}>
                  {style.icon}
                </div>
                <div className="rdp-step-content">
                  <p className="rdp-step-description">
                    {step.type === 'WALK' && `도보 ${formatTime(step.duration)}`}
                    {step.type === 'BUS' && `${step.name}번 버스`}
                    {step.type === 'SUBWAY' && `${step.name}`}
                    {step.type === 'BIKE' && `자전거`}
                  </p>
                  <p className="rdp-step-duration">{formatTime(step.duration)} 소요</p>
                  {step.start_name && step.end_name && (
                    <p className="rdp-step-places">{step.start_name} → {step.end_name}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
