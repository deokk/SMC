import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './MyPage.css';


const StatCard = ({ title, value, unit }) => (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-value">{value ?? 'N/A'} <span className="stat-unit">{value !== null && unit}</span></div>
    </div>
);

export default function MyPage() {
  const [patterns, setPatterns] = useState(null);
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

    const fetchPatterns = async () => {
      try {
        const patternsResponse = await fetch('/users/me/patterns', { headers: { 'Authorization': `Bearer ${token}` } });

        if (patternsResponse.ok) {
          const patternsData = await patternsResponse.json();
          setPatterns(patternsData);
        } else if (patternsResponse.status === 401) {
            throw new Error('세션이 만료되었습니다. 다시 로그인해주세요.');
        } else {
          console.error('사용자 패턴을 불러오는 데 실패했습니다.');
          throw new Error('사용자 패턴을 불러오는 데 실패했습니다.');
        }

      } catch (err) {
        if (err.message.includes('세션')) {
            alert(err.message);
            logout();
            navigate('/login');
        }
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPatterns();
  }, [isAuthenticated, token, navigate, logout]);

  if (isLoading) {
    return <div className="mp-container">로딩 중...</div>;
  }

  if (error) {
    return <div className="mp-container error">오류: {error}</div>;
  }

  return (
    <div className="mp-container">
      <header className="mp-header">
        <h1>{username}님의 이용 패턴</h1>
        <button onClick={() => navigate(-1)} className="mp-back-btn">뒤로 가기</button>
      </header>

      {patterns && (
        <section className="pattern-summary">
          <div className="stats-grid">
            <StatCard title="총 주행 횟수" value={patterns.total_trips} unit="회" />
            <StatCard title="평균 주행 시간" value={Math.round(patterns.average_duration_minutes)} unit="분" />
            <StatCard title="가장 활발한 요일" value={patterns.most_active_day} />
            <div className="stat-card large">
                <div className="stat-title">최애 출발 대여소</div>
                <div className="stat-value">{patterns.favorite_start_station_name || patterns.favorite_start_station_id || 'N/A'}</div>
            </div>
            <div className="stat-card large">
                <div className="stat-title">최애 도착 대여소</div>
                <div className="stat-value">{patterns.favorite_end_station_name || patterns.favorite_end_station_id || 'N/A'}</div>
            </div>
          </div>
        </section>
      )}

      <div className="history-link-container">
        <Link to="/ride-history" className="mp-detail-btn">상세 주행 내역 보기</Link>
      </div>
    </div>
  );
}
