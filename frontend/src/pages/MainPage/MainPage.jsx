import { useMemo, useState, useEffect, useCallback } from "react";
import { useOutletContext, useNavigate } from "react-router-dom"; // Add useNavigate
import KaKaoMap from "../../components/KaKaoMap";
import Header from "./components/Header";
import RouteCard from "./components/RouteCard";
import TimeCard from "./components/TimeCard";
import TimePickerModal from "./components/TimePickerModal";
import RouteResult from "./components/RouteResult";
import RouteDetailPanel from "./components/RouteDetailPanel";
import SideMenu from "../../components/SideMenu";
import useMediaQuery from "../../hooks/useMediaQuery";
import useGeolocation from "../../hooks/useGeolocation";
import StationInfoBox from "./components/StationInfoBox";
import HistoricalDataModal from "./components/HistoricalDataModal";
import { useAuth } from "../../context/AuthContext"; // Import useAuth
import "./MainPage.css";
import "./components/StationInfoBox.css";
import "./components/HistoricalDataModal.css";

const formatCurrentTime = () => {
  const now = new Date();
  const hour = now.getHours();
  const minute = now.getMinutes();
  const meridiem = hour < 12 ? "오전" : "오후";
  const hour12 = hour % 12 || 12;
  const dateLabel = "오늘";
  return `${dateLabel} ${meridiem} ${String(hour12).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
};
const addDays = (d, days) => {
  const nd = new Date(d);
  nd.setDate(nd.getDate() + days);
  return nd;
};
const parseTimeText = (timeText) => {
  try {
    const today = new Date();
    const parts = timeText.trim().split(/\s+/);
    if (parts.length < 3) return null;
    const datePart = parts[0];
    const meridiem = parts[1] === "오전" ? "오전" : "오후";
    const [hhStr, mmStr] = parts[2].split(":");
    if (!hhStr || !mmStr) return null;
    const hour = Math.min(12, Math.max(1, Number(hhStr)));
    const minute = Math.min(59, Math.max(0, Number(mmStr)));
    let date = new Date(today);
    if (datePart === "오늘") {
      date = new Date(today);
    } else if (datePart === "내일") {
      date = addDays(today, 1);
    } else {
      if (datePart.includes("월") && datePart.includes("일")) {
        const m = Number(datePart.split("월")[0]);
        const dd = Number(datePart.split("월")[1].replace("일", "").trim());
        const guessed = new Date(today.getFullYear(), m - 1, dd);
        date = guessed;
      } else { return null; }
    }
    return { date, meridiem, hour, minute };
  } catch { return null; }
};
const buildDateFromValue = (value) => {
  if (!value || !value.date) return null;
  const { date, meridiem, hour, minute } = value;
  const result = new Date(date);
  const hour24 = meridiem === "오전" ? (hour === 12 ? 0 : hour) : (hour === 12 ? 12 : hour + 12);
  result.setHours(hour24, minute, 0, 0);
  return result;
};

export default function MainPage() {
  const {
    from, setFrom, to, setTo,
    routes, setRoutes, isRoutesOpen, setIsRoutesOpen,
    selectedRoute, setSelectedRoute,
  } = useOutletContext();
  
  const navigate = useNavigate(); // For redirecting on auth error
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [timeText, setTimeText] = useState(formatCurrentTime());
  const [isTimeOpen, setIsTimeOpen] = useState(false);
  const [stations, setStations] = useState([]);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [isPredictionMode, setIsPredictionMode] = useState(false);
  const [predictionData, setPredictionData] = useState({});
  const [isPredicting, setIsPredicting] = useState(false);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const [nearbyStations, setNearbyStations] = useState([]);
  
  const { isAuthenticated, token, username, logout } = useAuth(); // Use useAuth hook
  const [isRiding, setIsRiding] = useState(false); // isRiding state is still for riding history, not location sharing
  
  // My Location Sharing State
  const [isSharingLocation, setIsSharingLocation] = useState(false);
  const handleToggleShareLocation = useCallback(() => {
    setIsSharingLocation(prevMode => !prevMode);
  }, []);

  const riderId = isAuthenticated && username ? username : "guest_user"; // Use authenticated username or guest
  const { location: myLocation, error: geoError } = useGeolocation(riderId, isSharingLocation); // Use isSharingLocation here
  
  const [selectedStation, setSelectedStation] = useState(null);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  const [searchMode, setSearchMode] = useState("multimodal"); // 'bicycle' or 'multimodal'

  // Friend Location Mode States
  const [isFriendLocationMode, setIsFriendLocationMode] = useState(false);
  const [friendLocations, setFriendLocations] = useState([]);
  const [isFetchingFriendLocations, setIsFetchingFriendLocations] = useState(false);

  const handleMarkerClick = (station) => {
    setSelectedStation(station);
  };
  
  const handleShowHistory = () => {
    setIsHistoryModalOpen(true);
  };
  
  const handleCloseStationBox = () => {
    setSelectedStation(null);
  };

  // Toggle Friend Location Mode
  const handleToggleFriendLocationMode = useCallback(() => {
    setIsFriendLocationMode(prevMode => !prevMode);
    // Clear friend locations when turning off the mode
    if (isFriendLocationMode) {
      setFriendLocations([]);
    }
    // No need to close side menu here, it's done in SideMenu.jsx
  }, [isFriendLocationMode]);


  useEffect(() => {
    if (geoError) alert(`위치 추적 에러: ${geoError}`);
  }, [geoError]);

  useEffect(() => {
    fetch('/stations/realtime').then(res => res.json()).then(setStations).catch(err => console.error("Failed to fetch real-time stations:", err));
  }, []);

  // Effect for fetching friend locations
  useEffect(() => {
    let intervalId;
    if (isFriendLocationMode && isAuthenticated && token) {
      const fetchFriendLocations = async () => {
        setIsFetchingFriendLocations(true);
        try {
          const response = await fetch('/friends/locations', {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (response.ok) {
            const data = await response.json();
            setFriendLocations(data);
          } else if (response.status === 401) {
            alert('세션이 만료되었습니다. 다시 로그인해주세요.');
            logout(); // Log out if token is invalid
            navigate('/login');
          } else {
            console.error("Failed to fetch friend locations:", response.status, response.statusText);
            setFriendLocations([]); // Clear on error
          }
        } catch (error) {
          console.error("Error fetching friend locations:", error);
          setFriendLocations([]); // Clear on error
        } finally {
          setIsFetchingFriendLocations(false);
        }
      };

      // Fetch immediately and then every 5 seconds
      fetchFriendLocations();
      intervalId = setInterval(fetchFriendLocations, 5000); // Poll every 5 seconds
    } else {
      // Clear friend locations and interval if mode is off or not authenticated
      setFriendLocations([]);
      if (intervalId) {
        clearInterval(intervalId);
      }
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isFriendLocationMode, isAuthenticated, token, logout, navigate]);

  const getBicycleSegment = async (start, end) => {
    try {
      const response = await fetch(`/api/bicycle-route?start_lat=${start.lat}&start_lng=${start.lon}&end_lat=${end.lat}&end_lng=${end.lon}`);
      if (!response.ok) return null;
      const data = await response.json();
      return {
        type: 'BICYCLE',
        distance: data.distance,
        duration: Math.round(data.duration / 60),
        polyline: data.path.map(p => [p.latitude, p.longitude]),
      };
    } catch (error) {
      console.error("자전거 경로 구간 탐색 실패:", error);
      return null;
    }
  };

  const handleSearch = async () => {
    setIsLoadingRoute(true);
    if (!window.kakao || !window.kakao.maps) {
      alert("지도 서비스가 로드되지 않았습니다.");
      setIsLoadingRoute(false);
      return;
    }
    const getCoords = (address) => new Promise((resolve, reject) => {
      const places = new window.kakao.maps.services.Places();
      places.keywordSearch(address, (result, status) => {
        if (status === window.kakao.maps.services.Status.OK && result.length > 0) {
          resolve({ lat: parseFloat(result[0].y), lon: parseFloat(result[0].x) });
        } else {
          const geocoder = new window.kakao.maps.services.Geocoder();
          geocoder.addressSearch(address, (geoResult, geoStatus) => {
            if (geoStatus === window.kakao.maps.services.Status.OK && geoResult.length > 0) {
              resolve({ lat: parseFloat(geoResult[0].y), lon: parseFloat(geoResult[0].x) });
            } else { reject(new Error("주소/장소 검색 실패: " + address)); }
          });
        }
      });
    });

    try {
      const startCoords = await getCoords(from);
      const endCoords = await getCoords(to);

      setRoutes([]);
      setSelectedRoute(null);
      setNearbyStations([]);

      if (searchMode === 'bicycle') {
        const bicycleRoute = await getBicycleSegment(startCoords, endCoords);
        if (bicycleRoute) {
          const fullRoute = {
            mode: 'BICYCLE',
            duration: bicycleRoute.duration,
            distance: bicycleRoute.distance,
            fare: 0,
            steps: [bicycleRoute],
          };
          setRoutes([fullRoute]);
          setIsRoutesOpen(true);
        } else {
          throw new Error("자전거 경로를 찾을 수 없습니다.");
        }
      } else { // 'multimodal'
        const transitResponse = await fetch("/route/optimized", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ start_lat: startCoords.lat, start_lon: startCoords.lon, end_lat: endCoords.lat, end_lon: endCoords.lon }),
        });
        if (!transitResponse.ok) {
          const errorData = await transitResponse.json();
          throw new Error(errorData.detail || "대중교통 경로 탐색 실패.");
        }
        const transitRoutes = await transitResponse.json();
        const augmentedRoutes = await Promise.all(
          transitRoutes.map(async (route) => {
            const newSteps = [...route.steps];
            let totalDuration = route.duration;
            let totalDistance = route.distance;
            if (route.first_station_coords) {
              const firstLeg = await getBicycleSegment(startCoords, { lat: route.first_station_coords.latitude, lon: route.first_station_coords.longitude });
              if (firstLeg) {
                newSteps.unshift(firstLeg);
                totalDuration += firstLeg.duration;
                totalDistance += firstLeg.distance;
              }
            }
            if (route.last_station_coords) {
              const lastLeg = await getBicycleSegment({ lat: route.last_station_coords.latitude, lon: route.last_station_coords.longitude }, endCoords);
              if (lastLeg) {
                newSteps.push(lastLeg);
                totalDuration += lastLeg.duration;
                totalDistance += lastLeg.distance;
              }
            }
            return { ...route, steps: newSteps, duration: totalDuration, distance: totalDistance };
          })
        );
        setRoutes(augmentedRoutes);
        setIsRoutesOpen(true);
      }
    } catch (error) {
      console.error("경로 검색 실패:", error);
      alert(error.message || "경로 검색 중 오류가 발생했습니다.");
    } finally {
      setIsLoadingRoute(false);
    }
  };

  useEffect(() => {
    const fetchNearbyStations = async () => {
      if (!selectedRoute || !selectedRoute.steps || selectedRoute.steps.length === 0) {
        setNearbyStations([]);
        return;
      }
  
      const { steps } = selectedRoute;
      const coordsToSearch = new Set();
  
      // 1. Overall Start
      const firstStep = steps[0];
      if (firstStep.polyline && firstStep.polyline.length > 0) {
        coordsToSearch.add(JSON.stringify({ lat: firstStep.polyline[0][0], lon: firstStep.polyline[0][1] }));
      }
  
      // 2. Overall End
      const lastStep = steps[steps.length - 1];
      if (lastStep.polyline && lastStep.polyline.length > 0) {
        coordsToSearch.add(JSON.stringify({ lat: lastStep.polyline[lastStep.polyline.length - 1][0], lon: lastStep.polyline[lastStep.polyline.length - 1][1] }));
      }
  
      // 3. Transit Start
      const firstTransitStep = steps.find(step => step.type !== 'WALK' && step.type !== 'BICYCLE');
      if (firstTransitStep?.polyline?.length > 0) {
        coordsToSearch.add(JSON.stringify({ lat: firstTransitStep.polyline[0][0], lon: firstTransitStep.polyline[0][1] }));
      }
  
      // 4. Transit End
      const lastTransitStep = [...steps].reverse().find(step => step.type !== 'WALK' && step.type !== 'BICYCLE');
      if (lastTransitStep?.polyline?.length > 0) {
        coordsToSearch.add(JSON.stringify({ lat: lastTransitStep.polyline[lastTransitStep.polyline.length - 1][0], lon: lastTransitStep.polyline[lastTransitStep.polyline.length - 1][1] }));
      }
      
      try {
        const uniqueCoords = Array.from(coordsToSearch).map(coord => JSON.parse(coord));
        const stationRequests = uniqueCoords.map(coord =>
          fetch(`http://127.0.0.1:8000/stations/near?lat=${coord.lat}&lon=${coord.lon}&limit=3&radius_km=0.3`).then(res => res.json())
        );
        const stationGroups = await Promise.all(stationRequests);
        
        const allStations = stationGroups.flat();
        const uniqueStations = Array.from(new Map(allStations.map(station => [station.station_id, station])).values());
        
        setNearbyStations(uniqueStations);
      } catch (error) {
        console.error("주변 대여소 검색 실패:", error);
        setNearbyStations([]);
      }
    };
  
    fetchNearbyStations();
  }, [selectedRoute]);
  
  const handleRouteSelect = (route) => {
    if (selectedRoute && selectedRoute === route) {
      setSelectedRoute(null);
    } else {
      setSelectedRoute(route);
    }
  };

  const handleTimeConfirm = useCallback(async (value) => {
    setTimeText(value.text);
    closeTimeModal();
    const selectedDate = buildDateFromValue(value);
    if (!selectedDate) return;
    const diffMinutes = Math.round((selectedDate - new Date()) / 60000);
    if (diffMinutes < 5) {
      setIsPredictionMode(false);
      setPredictionData({});
      return;
    }
    setIsPredicting(true);
    setIsPredictionMode(true);
    try {
      const results = await Promise.all(stations.map(station =>
        fetch(`/predict/hybrid/${station.station_id}?n_minutes=${diffMinutes}`).then(res => res.json()).catch(() => null)
      ));
      const newPredictionData = results.filter(Boolean).reduce((acc, res) => {
        acc[res.station_id] = res.predicted_bike_count;
        return acc;
      }, {});
      setPredictionData(newPredictionData);
    } catch (error) {
      console.error("Prediction fetch error:", error);
      setIsPredictionMode(false);
    } finally {
      setIsPredicting(false);
    }
  }, [stations]);

  const openTimeModal = () => setIsTimeOpen(true);
  const closeTimeModal = () => setIsTimeOpen(false);
  const openSideMenu = () => setIsSideMenuOpen(true);
  const closeSideMenu = () => setIsSideMenuOpen(false);
  const initialTimeValue = useMemo(() => parseTimeText(timeText), [timeText]);

  return (
    <div className="mp-root">
      {(isPredicting || isLoadingRoute || isFetchingFriendLocations) && <div className="mp-loading-overlay">{isLoadingRoute ? '경로 탐색 중...' : isFetchingFriendLocations ? '친구 위치 로딩 중...' : '예측 중...'}</div>}
      <div className="mp-top">
        <Header />
        {isMobile && selectedRoute && (
          <div className="mp-detail-panel-container">
            <RouteDetailPanel route={selectedRoute} onBack={() => setSelectedRoute(null)} />
          </div>
        )}
        {(!isMobile || !selectedRoute) && !isFriendLocationMode && ( // Add !isFriendLocationMode
          <section className="mp-cards">
            <RouteCard from={from} setFrom={setFrom} to={to} setTo={setTo} />
            <TimeCard timeText={timeText} setTimeText={setTimeText} openTimeModal={openTimeModal} />
          </section>
        )}
      </div>
      <main className="mp-map" aria-label="map area">
        <div className="mp-mapContainer">
          <KaKaoMap 
            stations={stations} 
            selectedRoute={selectedRoute}
            isPredictionMode={isPredictionMode}
            predictionData={predictionData}
            riderToTrack={isRiding ? riderId : null}
            myCurrentLocation={myLocation}
            nearbyStations={nearbyStations}
            onMarkerClick={handleMarkerClick}
            isFriendLocationMode={isFriendLocationMode} // Pass to map
            friendLocations={friendLocations}         // Pass to map
          />
          {isRoutesOpen && (
            (!isMobile || !selectedRoute) && (
              <div className="mp-routeOverlay">
                {!isMobile && selectedRoute ? (
                  <RouteDetailPanel route={selectedRoute} onBack={() => setSelectedRoute(null)} />
                ) : (
                  <RouteResult
                    routes={routes}
                    selectedRoute={selectedRoute}
                    isOpen={isRoutesOpen}
                    onBack={() => { setIsRoutesOpen(false); setSelectedRoute(null); }}
                    onRouteSelect={handleRouteSelect}
                  />
                )}
              </div>
            )
          )}
        </div>
      </main>
      <nav className="mp-bottom">
        <button className="mp-iconBtn" type="button" aria-label="메뉴" onClick={openSideMenu}>
          <img src="/list.svg" alt="메뉴" width="23" height="15" />
        </button>
        {!isFriendLocationMode && ( // Conditionally render search-related buttons
          <>
            <button 
              className="mp-mode-toggle" 
              onClick={() => setSearchMode(prev => prev === 'multimodal' ? 'bicycle' : 'multimodal')}
            >
              {searchMode === 'multimodal' ? '🚲+🚌' : '🚲'}
            </button>
            <button className="mp-cta" onClick={handleSearch} disabled={isLoadingRoute}>길찾기</button>
            <button className={`mp-iconBtn ${isRiding ? 'riding' : ''}`} onClick={() => setIsRiding(!isRiding)}>
              {isRiding ? '■' : '▶'}
            </button>
          </>
        )}
      </nav>
      <SideMenu 
        isOpen={isSideMenuOpen} 
        onClose={closeSideMenu} 
        onToggleFriendLocationMode={handleToggleFriendLocationMode}
        isFriendLocationMode={isFriendLocationMode}
        isSharingLocation={isSharingLocation} // Pass the state
        onToggleShareLocation={handleToggleShareLocation} // Pass the handler
      />
      <TimePickerModal open={isTimeOpen} initialValue={initialTimeValue} onClose={closeTimeModal} onConfirm={handleTimeConfirm} />
      <StationInfoBox 
        station={selectedStation} 
        onShowHistory={handleShowHistory}
        onClose={handleCloseStationBox} 
      />
      <HistoricalDataModal 
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        station={selectedStation}
      />
    </div>
  );
}