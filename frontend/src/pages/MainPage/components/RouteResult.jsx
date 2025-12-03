import { useState } from "react";
import "./RouteResult.css";

export default function RouteResult({ routes, isOpen, onBack }) {
  const [selectedMode, setSelectedMode] = useState(null);

  if (!isOpen || !routes) return null;

  const { transit, walking, bike } = routes;

  const formatTime = (minutes) => {
    if (minutes < 60) {
      return `${minutes}분`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}시간 ${mins}분` : `${hours}시간`;
  };

  // 선택된 모드의 상세 정보 (카카오맵 API에서 가져올 데이터)
  const modeDetails = {
    transit: {
      totalTime: 45,
      cost: 1200,
      startTime: "5:53",
      endTime: "6:12",
      walkingTime: 14, // 도보 전체 시간 (전 + 후)
      transitTime: 31,
      waitTime: 0,
      distance: 8.5,
      steps: [
        {
          type: "walking",
          time: 10,
          distance: 0.5,
          description: "건국대학교 서울캠퍼스에서 출발",
          isBeforeTransit: true,
        },
        {
          type: "transit",
          time: 31,
          distance: 8.0,
          description: "광진경찰서",
          lines: ["광진04", "광진03"],
          details: [
            { line: "광진04", time: "2분", stations: "1정류장", status: "보통" },
            { line: "광진03", time: "11분", stations: "13정류장", status: "여유" },
          ],
        },
        {
          type: "walking",
          time: 4,
          distance: 0.2,
          description: "구의역4번출구",
          isBeforeTransit: false,
        },
      ],
    },
    walking: {
      totalTime: 28,
      distance: 2.1,
      steps: [
        { type: "walking", time: 28, distance: 2.1, description: "도보로 이동" },
      ],
    },
    bike: {
      totalTime: 18,
      distance: 2.8,
      steps: [
        { type: "bike", time: 18, distance: 2.8, description: "자전거로 이동" },
      ],
    },
  };

  if (selectedMode === "transit") {
    const details = modeDetails.transit;
    const totalLength = details.walkingTime + details.transitTime + (details.waitTime || 0);

    const walkingPercent = (details.walkingTime / totalLength) * 100;
    const transitPercent = (details.transitTime / totalLength) * 100;

    return (
      <div className="rr-container">
        <button className="rr-backBtn" onClick={() => setSelectedMode(null)}>
          ← 돌아가기
        </button>

        <div className="rr-transitHeader">
          <h3 className="rr-transitTitle">최적</h3>
          <div className="rr-transitTime">{formatTime(details.totalTime)}</div>
          <div className="rr-transitSubInfo">
            {details.startTime} - {details.endTime} {details.cost}원
          </div>
        </div>

        {/* 타임라인 바 */}
        <div className="rr-timelineBarContainer">
          <div className="rr-timelineBar">
            <div
              className="rr-timelineSegment rr-timelineSegment--walking"
              style={{ width: `${walkingPercent}%` }}
              title={`도보 ${formatTime(details.walkingTime)}`}
            >
              <span className="rr-segmentLabel">{formatTime(details.walkingTime)}</span>
            </div>
            <div
              className="rr-timelineSegment rr-timelineSegment--transit"
              style={{ width: `${transitPercent}%` }}
              title={`대중교통 ${formatTime(details.transitTime)}`}
            >
              <span className="rr-segmentLabel">{formatTime(details.transitTime)}</span>
            </div>
          </div>
        </div>

        {/* 경로 상세 */}
        <div className="rr-transitDetails">
          {details.steps.map((step, idx) => (
            <div key={idx} className="rr-transitStep">
              <div className="rr-transitStepIcon">
                {step.type === "walking" && "🚶"}
                {step.type === "transit" && "🚌"}
              </div>
              <div className="rr-transitStepContent">
                <div className="rr-stepHeader">
                  <span className="rr-stepMode">
                    {step.type === "walking" && "도보"}
                    {step.type === "transit" && "대중교통"}
                  </span>
                  <span className="rr-stepDuration">{formatTime(step.time)}</span>
                </div>
                <div className="rr-stepLocation">{step.description}</div>

                {/* 대중교통 상세 정보 */}
                {step.details && (
                  <div className="rr-transitLineDetails">
                    <div className="rr-transitLines">
                      {step.lines.map((line, i) => (
                        <span key={i} className="rr-transitLine">
                          {line}
                        </span>
                      ))}
                    </div>
                    {step.details.map((detail, i) => (
                      <div key={i} className="rr-transitLineInfo">
                        <span className="rr-lineIcon">🚌</span>
                        <span className="rr-lineName">{detail.line}</span>
                        <span className="rr-lineTime">{detail.time}</span>
                        <span className="rr-lineStations">{detail.stations}</span>
                        <span className={`rr-lineStatus rr-lineStatus--${detail.status === "보통" ? "normal" : "comfort"}`}>
                          {detail.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (selectedMode) {
    const details = modeDetails[selectedMode];
    return (
      <div className="rr-container">
        <button className="rr-backBtn" onClick={() => setSelectedMode(null)}>
          ← 돌아가기
        </button>

        <div className="rr-detailHeader">
          <h3 className="rr-detailTitle">
            {selectedMode === "transit" && "🚌 대중교통"}
            {selectedMode === "walking" && "🚶 도보"}
            {selectedMode === "bike" && "🚴 자전거"}
          </h3>
          <div className="rr-detailTime">{formatTime(details.totalTime)}</div>
        </div>

        {selectedMode === "transit" && details.walkingTime && (
          <div className="rr-walkingInfo">
            <span>🚶 도보: {formatTime(details.walkingTime)}</span>
            <span>🚌 대중교통: {formatTime(details.transitTime)}</span>
          </div>
        )}

        <div className="rr-distanceInfo">거리: {details.distance}km</div>

        <div className="rr-stepsList">
          {details.steps.map((step, idx) => (
            <div key={idx} className="rr-step">
              <div className="rr-stepIcon">
                {step.type === "walking" && "🚶"}
                {step.type === "transit" && "🚌"}
                {step.type === "bike" && "🚴"}
              </div>
              <div className="rr-stepContent">
                <div className="rr-stepDesc">{step.description}</div>
                <div className="rr-stepTime">
                  {formatTime(step.time)} · {step.distance}km
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rr-container">
      <button className="rr-backBtn" onClick={onBack}>
        ← 뒤로
      </button>

      <div className="rr-header">
        <h3 className="rr-title">경로 선택</h3>
      </div>

      <div className="rr-modeSelector">
        {transit && (
          <button
            className="rr-modeBtn"
            onClick={() => setSelectedMode("transit")}
          >
            <div className="rr-modeIcon">🚌</div>
            <div className="rr-modeInfo">
              <div className="rr-modeLabel">대중교통</div>
              <div className="rr-modeTime">{formatTime(transit)}</div>
            </div>
          </button>
        )}

        {walking && (
          <button
            className="rr-modeBtn"
            onClick={() => setSelectedMode("walking")}
          >
            <div className="rr-modeIcon">🚶</div>
            <div className="rr-modeInfo">
              <div className="rr-modeLabel">도보</div>
              <div className="rr-modeTime">{formatTime(walking)}</div>
            </div>
          </button>
        )}

        {bike && (
          <button
            className="rr-modeBtn"
            onClick={() => setSelectedMode("bike")}
          >
            <div className="rr-modeIcon">🚴</div>
            <div className="rr-modeInfo">
              <div className="rr-modeLabel">자전거</div>
              <div className="rr-modeTime">{formatTime(bike)}</div>
            </div>
          </button>
        )}
      </div>
    </div>
  );
}
