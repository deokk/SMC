import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useState } from "react";
import AddFriendModal from "./AddFriendModal"; // Add this import
import "./SideMenu.css";

export default function SideMenu({
  isOpen,
  onClose,
  onToggleFriendLocationMode,
  isFriendLocationMode,
  isSharingLocation,
  onToggleShareLocation,
}) {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [showAddFriendModal, setShowAddFriendModal] = useState(false); // New state

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
      handleProtectedAction("친구 추가"); // Use the protected action handler
    } else {
      setShowAddFriendModal(true); // Open the modal
      onClose(); // Close the side menu
    }
  };

  const handleFriendLocationClick = () => {
    if (!isAuthenticated) {
      handleProtectedAction("친구 위치");
    } else {
      onToggleFriendLocationMode(); // Toggle the mode
      onClose(); // Now close the side menu immediately after toggling friend location
    }
  };

  const handleShareLocationClick = () => {
    if (!isAuthenticated) {
      handleProtectedAction("위치 공유");
    } else {
      onToggleShareLocation();
      onClose(); // Close the side menu
    }
  };

  const handleLogout = () => {
    logout();
    onClose();
    navigate("/"); // Navigate to home page after logout
  };

  return (
    <>
      {/* 오버레이 */}
      <div className="sm-overlay" onClick={onClose} />

      {/* 사이드 메뉴 */}
      <div className="sm-menu">
        <div className="sm-header">
          <h3 className="sm-title">메뉴</h3>
          <button className="sm-closeBtn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="sm-content">
          <button
            className={`sm-item ${isSharingLocation ? "active" : ""}`} // Add active class
            onClick={handleShareLocationClick}
          >
            <img src="/location.svg" alt="위치 공유" className="sm-itemIcon" />
            <span className="sm-itemLabel">
              {isSharingLocation ? "위치 공유 끄기" : "위치 공유"}
            </span>{" "}
            {/* Dynamic label */}
            <span className="sm-itemArrow">›</span>
          </button>

          <button
            className={`sm-item ${isFriendLocationMode ? "active" : ""}`} // Add active class
            onClick={handleFriendLocationClick}
          >
            <img
              src="/pin.svg"
              alt="친구 위치"
              className="sm-itemIcon"
              width="20"
              height="20"
            />
            <span className="sm-itemLabel">
              {isFriendLocationMode ? "친구 위치 끄기" : "친구 위치"}
            </span>{" "}
            {/* Dynamic label */}
            <span className="sm-itemArrow">›</span>
          </button>

          <button className="sm-item" onClick={handleAddFriendClick}>
            <img
              src="/plusfriend.svg"
              alt="친구 추가"
              className="sm-itemIcon"
              width="20"
              height="20"
            />
            <span className="sm-itemLabel">친구 추가</span>
            <span className="sm-itemArrow">›</span>
          </button>

          <button
            className="sm-item"
            onClick={() => handleProtectedAction("AI 패턴 분석")}
          >
            <img
              src="/ai.svg"
              alt="AI 패턴 분석"
              className="sm-itemIcon"
              width="20"
              height="20"
            />
            <span className="sm-itemLabel">AI 패턴 분석</span>
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
                <img
                  src="/login.svg"
                  alt="로그인"
                  className="sm-itemIcon"
                  width="20"
                  height="20"
                />
                <span className="sm-itemLabel">로그인</span>
              </Link>

              <Link to="/register" className="sm-item" onClick={onClose}>
                <img
                  src="/registration.svg"
                  alt="회원가입"
                  className="sm-itemIcon"
                  width="20"
                  height="20"
                />
                <span className="sm-itemLabel">회원가입</span>
              </Link>
            </>
          )}
        </div>
      </div>
      {showAddFriendModal && (
        <AddFriendModal onClose={() => setShowAddFriendModal(false)} />
      )}
    </>
  );
}
