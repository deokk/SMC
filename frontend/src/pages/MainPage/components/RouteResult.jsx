import "./RouteResult.css";

const getModeIcon = (mode) => {
  if (mode.toUpperCase() === "TRANSIT") return "🚌";
  if (mode.toUpperCase() === "WALK") return "🚶";
  if (mode.toUpperCase() === "BIKE") return "🚴";
  return "📍";
};

const SUBWAY_LINE_COLORS = {
  "1호선": "#0052A4", "2호선": "#00A84D", "3호선": "#EF7C1C", "4호선": "#00A5DE", 
  "5호선": "#996CAC", "6호선": "#CD7C2C", "7호선": "#747F00", "8호선": "#EA545D", 
  "9호선": "#BDB092", "수인분당선": "#F5A200", "신분당선": "#D31145", 
  "공항철도": "#7C8D93", "경의중앙선": "#77C4A3", "우이신설선": "#B0CE00", 
  "default": "#A1A1A1" // 기본값
};

const getTransportStyle = (type, name = '') => {
  const t = type.toUpperCase();
  if (t === "SUBWAY") {
    const color = SUBWAY_LINE_COLORS[name] || SUBWAY_LINE_COLORS.default;
    return { color, bg: `${color}20`, icon: "🚇" };
  }
  if (t === "BUS") return { color: "#3b6dc0", bg: "#eef4ff", icon: "🚌" };
  if (t === "WALK") return { color: "#888", bg: "transparent", icon: "🚶" };
  return { color: "#333", bg: "#eee", icon: "📍" };
};

const formatTime = (minutes) => {
  if (minutes < 60) return `${minutes}분`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}시간 ${mins}분` : `${hours}시간`;
};

export default function RouteResult({ routes, isOpen, onBack, onRouteSelect, selectedRoute }) {
  if (!isOpen || !routes) return null;

  return (
    <div className="rr-container">
       <button className="rr-backBtn" onClick={onBack}>← 뒤로</button>
      <h3 className="rr-title">추천 경로</h3>
      <div className="rr-list">
        {routes.map((route, index) => {
          const mainSteps = route.steps.filter(s => s.type !== 'WALK' && s.type !== 'BICYCLE');

          return (
            <button 
              key={index} 
              className={`rr-card ${selectedRoute === route ? 'rr-card--selected' : ''}`} 
              onClick={() => onRouteSelect(route)}
            >
              <div className="rr-card-left">
                <div className="rr-card-time">{formatTime(route.duration)}</div>
                <div className="rr-card-info">
                  {formatTime(route.steps.filter(s=>s.type==='WALK').reduce((sum,s)=>sum+s.duration,0))} 도보
                </div>
              </div>
              
              <div className="rr-card-right">
                <div className="rr-badges">
                  {mainSteps.map((step, i) => {
                    const style = getTransportStyle(step.type, step.name); // Pass name to getTransportStyle
                    let badgeText = step.name || '';
                    if (step.type === 'BUS') {
                        badgeText = `${step.name}번`;
                    } else if (step.type === 'SUBWAY') {
                        badgeText = step.name; // ODsay에서 이미 'N호선' 형태로 옴
                    }
                    return (
                      <span key={i} className="rr-badge" style={{ color: style.color, backgroundColor: style.bg }}>
                        {badgeText}
                      </span>
                    );
                  })}
                </div>
                 <div className="rr-card-info">
                  {route.fare?.toLocaleString()}원
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}