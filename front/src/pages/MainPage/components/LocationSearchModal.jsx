import { useEffect, useRef, useState } from "react";
import useKakaoLoader from "../../../hooks/useKakaoLoader.js";
import "./LocationSearchModal.css";

export default function LocationSearchModal({
  isOpen,
  onClose,
  onSelect,
  title,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const sdkReady = useKakaoLoader();
  const [searchInput, setSearchInput] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedMarker, setSelectedMarker] = useState(null);

  // 지도 초기화
  useEffect(() => {
    if (!isOpen || !sdkReady || !window.kakao?.maps) return;

    if (mapRef.current) return;

    window.kakao.maps.load(() => {
      const center = new window.kakao.maps.LatLng(37.5408, 127.0793);
      mapRef.current = new window.kakao.maps.Map(containerRef.current, {
        center,
        level: 4,
      });
    });
  }, [isOpen, sdkReady]);

  // 장소 검색
  const handleSearch = (keyword) => {
    if (!keyword.trim() || !window.kakao?.maps) return;

    const ps = new window.kakao.maps.services.Places();
    ps.keywordSearch(keyword, (data, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        setSearchResults(data);
      } else {
        setSearchResults([]);
      }
    });
  };

  // 결과 선택 시 지도에 마커 표시
  const handleSelectResult = (result) => {
    if (!mapRef.current) return;

    const lat = parseFloat(result.y);
    const lng = parseFloat(result.x);
    const pos = new window.kakao.maps.LatLng(lat, lng);

    mapRef.current.setCenter(pos);

    // 기존 마커 제거
    if (markerRef.current) {
      markerRef.current.setMap(null);
    }

    // 새 마커 추가
    markerRef.current = new window.kakao.maps.Marker({
      position: pos,
      map: mapRef.current,
    });

    setSelectedMarker({
      name: result.place_name,
      lat,
      lng,
    });
  };

  // 확인 버튼
  const handleConfirm = () => {
    if (selectedMarker) {
      onSelect(selectedMarker.name);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="lsm-overlay">
      <div className="lsm-modal">
        <div className="lsm-header">
          <h2 className="lsm-title">{title}</h2>
          <button className="lsm-closeBtn" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>

        <div className="lsm-searchBox">
          <input
            type="text"
            className="lsm-searchInput"
            placeholder="장소 검색..."
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              handleSearch(e.target.value);
            }}
            aria-label="장소 검색"
          />
        </div>

        <div className="lsm-container">
          <div className="lsm-map" ref={containerRef} />

          <div className="lsm-results">
            {searchResults.length > 0 ? (
              <ul className="lsm-list">
                {searchResults.map((result) => (
                  <li
                    key={result.id}
                    className={`lsm-item ${
                      selectedMarker?.name === result.place_name
                        ? "lsm-item--selected"
                        : ""
                    }`}
                    onClick={() => handleSelectResult(result)}
                  >
                    <div className="lsm-itemName">{result.place_name}</div>
                    <div className="lsm-itemAddr">
                      {result.road_address_name || result.address_name}
                    </div>
                  </li>
                ))}
              </ul>
            ) : searchInput.trim() ? (
              <div className="lsm-empty">검색 결과가 없습니다</div>
            ) : (
              <div className="lsm-placeholder">장소를 검색해주세요</div>
            )}
          </div>
        </div>

        <div className="lsm-footer">
          <button className="lsm-cancelBtn" onClick={onClose}>
            취소
          </button>
          <button
            className="lsm-confirmBtn"
            onClick={handleConfirm}
            disabled={!selectedMarker}
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}
