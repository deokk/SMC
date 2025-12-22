import React from 'react';
import './StationInfoBox.css';

export default function StationInfoBox({ station, onShowHistory, onClose }) {
  if (!station) {
    return null;
  }

  return (
    <div className="station-info-box">
      <button className="sib-close-btn" onClick={onClose}>×</button>
      <div className="sib-title">
        {station.station_display_name || station.station_name} ({station.station_id})
      </div>
      <div className="sib-content">
        <div>이용 가능: {station.available_bikes}대</div>
      </div>
      <div className="sib-footer">
        <button className="sib-history-btn" onClick={() => onShowHistory(station)}>
          과거 데이터 보기
        </button>
      </div>
    </div>
  );
}
