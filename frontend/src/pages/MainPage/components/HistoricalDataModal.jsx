import React, { useState, useEffect } from 'react';
import './HistoricalDataModal.css';

const PeriodTab = ({ period, label, isActive, onClick }) => (
  <button
    className={`hdm-tab ${isActive ? 'active' : ''}`}
    onClick={() => onClick(period)}
  >
    {label}
  </button>
);

const DataRow = ({ item, maxCapacity }) => {
  const capacity = maxCapacity > 0 ? maxCapacity : 20; // Fallback to 20 if capacity is 0 or not available
  const widthPercentage = Math.min(100, (item.avg_available_bikes / capacity) * 100);

  return (
    <div className="hdm-row">
      <span className="hdm-hour">{item.hour}:00</span>
      <div className="hdm-bar-container">
        <div 
          className="hdm-bar" 
          style={{ width: `${widthPercentage}%` }}
        />
      </div>
      <span className="hdm-value">{item.avg_available_bikes.toFixed(1)}대</span>
    </div>
  );
};

export default function HistoricalDataModal({ isOpen, onClose, station }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activePeriod, setActivePeriod] = useState('yesterday');

  useEffect(() => {
    if (isOpen && station) {
      setIsLoading(true);
      setError(null);
      setData(null);
      
      fetch(`http://127.0.0.1:8000/stations/${station.station_id}/hourly_comparison`)
        .then(res => {
          if (!res.ok) {
            throw new Error('데이터를 불러오는 데 실패했습니다.');
          }
          return res.json();
        })
        .then(fetchedData => {
          setData(fetchedData);
        })
        .catch(err => {
          setError(err.message);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  }, [isOpen, station]);

  if (!isOpen) {
    return null;
  }

  const activeData = data ? data[activePeriod]?.hourly_data : [];

  return (
    <div className="hdm-overlay">
      <div className="hdm-modal">
        <div className="hdm-header">
          <h2 className="hdm-title">{station?.station_name || '과거 데이터'}</h2>
          <button className="hdm-close-btn" onClick={onClose}>×</button>
        </div>
        <div className="hdm-tabs">
          <PeriodTab period="yesterday" label="1일 전" isActive={activePeriod === 'yesterday'} onClick={setActivePeriod} />
          <PeriodTab period="two_days_ago" label="2일 전" isActive={activePeriod === 'two_days_ago'} onClick={setActivePeriod} />
          <PeriodTab period="last_week" label="1주 전" isActive={activePeriod === 'last_week'} onClick={setActivePeriod} />
        </div>
        <div className="hdm-content">
          {isLoading && <div className="hdm-message">로딩 중...</div>}
          {error && <div className="hdm-message hdm-error">{error}</div>}
          {data && !isLoading && (
            activeData && activeData.length > 0 ? (
              activeData.map(item => <DataRow key={item.hour} item={item} maxCapacity={station.station_capacity} />)
            ) : (
              <div className="hdm-message">해당 기간의 데이터가 없습니다.</div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
