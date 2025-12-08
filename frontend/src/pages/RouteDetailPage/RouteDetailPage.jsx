import { useEffect } from "react";
import { useOutletContext, useNavigate } from "react-router-dom";
import "./RouteDetailPage.css";

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
    "default": "#A1A1A1" // 기본값
  };

  const t = type.toUpperCase();
  if (t === "SUBWAY") {
    const color = SUBWAY_LINE_COLORS[name] || SUBWAY_LINE_COLORS.default;
    return { color, bg: `${color}20`, icon: "🚇" };
  }
  if (t === "BUS") return { color: "#3b6dc0", bg: "#eef4ff", icon: "🚌" };
  if (t === "WALK") return { color: "#888", bg: "transparent", icon: "🚶" };
  if (t === "BIKE") return { color: "#007bff", bg: "#e6f2ff", icon: "🚴" }; // Assuming a bike style
  return { color: "#333", bg: "#eee", icon: "📍" };
};


export default function RouteDetailPage() {
  const { selectedRoute } = useOutletContext();
  const navigate = useNavigate();

  useEffect(() => {
    // If no route data is in the context, redirect back to main page
    if (!selectedRoute) {
      navigate("/");
    }
  }, [selectedRoute, navigate]);

  if (!selectedRoute) {
    return null; // or a loading spinner
  }

  const route = selectedRoute; // for convenience

  return (
    <div className="rd-container">
      <button className="rd-backBtn" onClick={() => navigate(-1)}>
        ← 뒤로
      </button>
      <h2 className="rd-title">경로 상세 정보</h2>

      <div className="rd-summary">
        <p>총 소요 시간: {formatTime(route.duration)}</p>
        <p>총 요금: {route.fare?.toLocaleString()}원</p>
        <p>도보 시간: {formatTime(route.steps.filter(s=>s.type==='WALK').reduce((sum,s)=>sum+s.duration,0))}</p>
      </div>

      <div className="rd-steps">
        <h3>세부 경로</h3>
        {route.steps.map((step, index) => {
          const style = getTransportStyle(step.type, step.name);
          return (
            <div key={index} className="rd-step-card">
              <div className="rd-step-icon" style={{ backgroundColor: style.bg, color: style.color }}>
                {style.icon}
              </div>
              <div className="rd-step-content">
                <p className="rd-step-description">
                  {step.type === 'WALK' && `도보 ${formatTime(step.duration)}`}
                  {step.type === 'BUS' && `버스 ${step.name}번, ${formatTime(step.duration)}`}
                  {step.type === 'SUBWAY' && `지하철 ${step.name}, ${formatTime(step.duration)}`}
                  {step.type === 'BIKE' && `자전거 ${formatTime(step.duration)}`}
                </p>
                {step.start_name && step.end_name && (
                  <p className="rd-step-places">{step.start_name} → {step.end_name}</p>
                )}
                {/* Add more details if available in step.details for transit */}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
