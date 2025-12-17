import { useState } from "react";
import LocationSearchModal from "./LocationSearchModal";

export default function RouteCard({ from, setFrom, to, setTo }) {
  const [isFromModalOpen, setIsFromModalOpen] = useState(false);
  const [isToModalOpen, setIsToModalOpen] = useState(false);

  return (
    <>
      <div className="mp-card mp-card--route">
        <div className="mp-routeCol" aria-hidden="true">
          <img
            src="/departure.svg"
            alt="출발지"
            className="mp-dot mp-dot--from"
          />
          <div className="mp-routeLine" />
          <div className="mp-dot mp-dot--to" />
        </div>

        <div className="mp-fields">
          <div className="mp-row">
            <input
              className="mp-input"
              value={from}
              onClick={() => setIsFromModalOpen(true)}
              readOnly
              placeholder="출발지"
              aria-label="출발지"
            />
            <button
              className="mp-clear"
              onClick={() => setFrom("")}
              aria-label="출발지 지우기"
            >
              ×
            </button>
          </div>
          <div className="mp-divider" />
          <div className="mp-row">
            <input
              className="mp-input"
              value={to}
              onClick={() => setIsToModalOpen(true)}
              readOnly
              placeholder="도착지"
              aria-label="도착지"
            />
            <button
              className="mp-clear"
              onClick={() => setTo("")}
              aria-label="도착지 지우기"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <LocationSearchModal
        isOpen={isFromModalOpen}
        onClose={() => setIsFromModalOpen(false)}
        onSelect={setFrom}
        title="출발지 검색"
      />
      <LocationSearchModal
        isOpen={isToModalOpen}
        onClose={() => setIsToModalOpen(false)}
        onSelect={setTo}
        title="도착지 검색"
      />
    </>
  );
}
