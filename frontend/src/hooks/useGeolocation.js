import { useState, useEffect } from 'react';

const useGeolocation = (riderId, isActive = false) => {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let watchId = null;

    if (isActive) {
      const handleSuccess = (position) => {
        const { latitude, longitude } = position.coords;
        const newLocation = { latitude, longitude };
        setLocation(newLocation);
        
        if (riderId) {
          fetch(`http://127.0.0.1:8000/riders/${riderId}/location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newLocation),
          }).catch(err => console.error("위치 전송 실패:", err));
        }
      };

      const handleError = (err) => {
        setError(err.message);
      };

      if (navigator.geolocation) {
        watchId = navigator.geolocation.watchPosition(handleSuccess, handleError, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        });
      } else {
        setError("이 브라우저에서는 Geolocation이 지원되지 않습니다.");
      }
    } else {
      // GPS가 꺼지면 위치와 에러를 초기화
      setLocation(null);
      setError(null);
    }

    return () => {
      if (watchId) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [riderId, isActive]);

  return { location, error };
};

export default useGeolocation;
