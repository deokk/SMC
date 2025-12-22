import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import './RideHistoryPage.css';

// Helper functions
const formatDuration = (start, end) => {
  if (!start || !end) return 'N/A';
  const durationMs = new Date(end) - new Date(start);
  const minutes = Math.floor(durationMs / 60000);
  const seconds = Math.floor((durationMs % 60000) / 1000);
  return `${minutes}분 ${seconds}초`;
};

const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A';
  return new Date(timestamp).toLocaleString('ko-KR');
};

export default function RideHistoryPage() {
  const [rides, setRides] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const { token, isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      alert("로그인이 필요합니다.");
      navigate('/login');
      return;
    }

    const fetchRides = async () => {
      try {
        const response = await fetch('/users/me/rides', {
          headers: { 'Authorization': `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();
          data.sort((a, b) => new Date(b.start_time) - new Date(a.start_time));
          setRides(data);
        } else if (response.status === 401) {
          alert("세션이 만료되었습니다. 다시 로그인해주세요.");
          logout();
          navigate('/login');
        } else {
          throw new Error('주행 기록을 불러오는 데 실패했습니다.');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRides();
  }, [isAuthenticated, token, navigate, logout]);

  if (isLoading) {
    return <div className="rhp-container">로딩 중...</div>;
  }

  if (error) {
    return <div className="rhp-container error">오류: {error}</div>;
  }

  return (
    <div className="rhp-container">
      <header className="rhp-header">
        <h1>{username}님의 상세 주행 내역</h1>
        <button onClick={() => navigate(-1)} className="rhp-back-btn">뒤로 가기</button>
      </header>
      {rides.length === 0 ? (
        <p>주행 기록이 없습니다.</p>
      ) : (
        <div className="rhp-table-container">
          <table className="rhp-ride-table">
            <thead>
              <tr>
                <th>출발 시간</th>
                <th>종료 시간</th>
                <th>주행 시간</th>
                <th>출발 대여소</th>
                <th>도착 대여소</th>
              </tr>
            </thead>
            <tbody>
              {rides.map((ride) => (
                <tr key={ride.id}>
                  <td>{formatTimestamp(ride.start_time)}</td>
                  <td>{formatTimestamp(ride.end_time)}</td>
                  <td>{formatDuration(ride.start_time, ride.end_time)}</td>
                  <td>{ride.start_station_name || ride.start_station_id || 'N/A'}</td>
                  <td>{ride.end_station_name || ride.end_station_id || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
