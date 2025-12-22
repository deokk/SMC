import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./SideMenu.css";

export default function SideMenu({
  isOpen,
  onClose,
  onToggleFriendLocationMode,
  isFriendLocationMode,
  isSharingLocation,
  onToggleShareLocation,
  setIsAddFriendModalOpen, // Receive setter from parent
}) {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleProtectedAction = (featureName) => {
    if (!isAuthenticated) {
      alert("로그인이 필요합니다.");
      navigate("/login");
      onClose();
    } else {
      // Placeholder for actual feature
      alert(`${featureName} 기능은 현재 구현 중입니다.`);
    }
  };

  const handleAddFriendClick = () => {
    if (!isAuthenticated) {
      handleProtectedAction('친구 추가');
    } else {
      setIsAddFriendModalOpen(true); // Use setter from props
      onClose();
    }
  };

  const handleFriendLocationClick = () => {
    if (!isAuthenticated) {
      handleProtectedAction('친구 위치');
    } else {
      onToggleFriendLocationMode();
      onClose();
    }
  };
  
  const handleShareLocationClick = () => {
    if (!isAuthenticated) {
      handleProtectedAction('위치 공유');
    } else {
      onToggleShareLocation();
      onClose();
    }
  };

  const handleLogout = () => {
    logout();
    onClose();
    navigate('/');
  };

  return (
    <>
      <div className="sm-overlay" onClick={onClose} />
      <div className="sm-menu">
        <div className="sm-header">
          <h3 className="sm-title">메뉴</h3>
          <button className="sm-closeBtn" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="sm-content">
          <button
            className={`sm-item ${isSharingLocation ? "active" : ""}`}
            onClick={handleShareLocationClick}
          >
            <img src="/location.svg" alt="위치 공유" className="sm-itemIcon" />
            <span className="sm-itemLabel">
              {isSharingLocation ? "위치 공유 끄기" : "위치 공유"}
            </span>
            <span className="sm-itemArrow">›</span>
          </button>
          <button
            className={`sm-item ${isFriendLocationMode ? "active" : ""}`}
            onClick={handleFriendLocationClick}
          >
            <img src="/pin.svg" alt="친구 위치" className="sm-itemIcon" width="20" height="20" />
            <span className="sm-itemLabel">
              {isFriendLocationMode ? "친구 위치 끄기" : "친구 위치"}
            </span>
            <span className="sm-itemArrow">›</span>
          </button>
          <button className="sm-item" onClick={handleAddFriendClick}>
            <img src="/plusfriend.svg" alt="친구 추가" className="sm-itemIcon" width="20" height="20" />
            <span className="sm-itemLabel">친구 추가</span>
            <span className="sm-itemArrow">›</span>
          </button>
          <button
            className="sm-item"
            onClick={() => {
              if (isAuthenticated) {
                navigate("/mypage");
              } else {
                alert("로그인이 필요합니다.");
                navigate("/login");
              }
              onClose();
            }}
          >
            <img src="/list.svg" alt="마이페이지" className="sm-itemIcon" width="20" height="20" />
            <span className="sm-itemLabel">마이페이지</span>
            <span className="sm-itemArrow">›</span>
          </button>
          <div className="sm-divider"></div>
          {isAuthenticated ? (
            <button className="sm-item" onClick={handleLogout}>
              <span className="sm-itemIcon">🔒</span>
              <span className="sm-itemLabel">로그아웃</span>
            </button>
          ) : (
            <>
              <Link to="/login" className="sm-item" onClick={onClose}>
                <img src="/login.svg" alt="로그인" className="sm-itemIcon" width="20" height="20" />
                <span className="sm-itemLabel">로그인</span>
              </Link>
              <Link to="/register" className="sm-item" onClick={onClose}>
                <img src="/registration.svg" alt="회원가입" className="sm-itemIcon" width="20" height="20" />
                <span className="sm-itemLabel">회원가입</span>
              </Link>
            </>
          )}
        </div>
      </div>
    </>
  );
}
