import "./SideMenu.css";

export default function SideMenu({ isOpen, onClose }) {
  if (!isOpen) return null;

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
          <div className="sm-item">
            <span className="sm-itemIcon">📍</span>
            <span className="sm-itemLabel">위치 공유</span>
            <span className="sm-itemArrow">›</span>
          </div>

          <div className="sm-item">
            <span className="sm-itemIcon">✓</span>
            <span className="sm-itemLabel">친구 위치</span>
            <span className="sm-itemArrow">›</span>
          </div>

          <div className="sm-item">
            <span className="sm-itemIcon">👥</span>
            <span className="sm-itemLabel">친구 추가</span>
            <span className="sm-itemArrow">›</span>
          </div>

          <div className="sm-item">
            <span className="sm-itemIcon">📋</span>
            <span className="sm-itemLabel">AI 패턴 분석</span>
            <span className="sm-itemArrow">›</span>
          </div>
        </div>
      </div>
    </>
  );
}
