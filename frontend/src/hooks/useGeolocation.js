import { useState, useEffect } from 'react';

const useGeolocation = (riderId, isSharingLocation = false) => {
  const [location, setLocation] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let watchId = null;

    if (isSharingLocation) { // Use isSharingLocation here
      const handleSuccess = (position) => {
        const { latitude, longitude } = position.coords;
        const newLocation = { latitude, longitude, is_sharing: isSharingLocation }; // Include is_sharing
        setLocation(newLocation);
        
        if (riderId) {
          fetch(`/riders/${riderId}/location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newLocation),
          }).catch(err => console.error("위치 전송 실패:", err));
        }
      };

      const handleError = (err) => {
        console.error("Geolocation error:", err);
        setError(err.message);
      };

      if (navigator.geolocation) {
        watchId = navigator.geolocation.watchPosition(handleSuccess, handleError, {
          enableHighAccuracy: true,
          timeout: 20000,
          maximumAge: 0
        });
      } else {
        setError("이 브라우저에서는 Geolocation이 지원되지 않습니다.");
      }
    } else {
      // GPS가 꺼지면 위치와 에러를 초기화
      setLocation(null);
      setError(null);
      // When sharing is turned off, also send a final update to backend to set is_sharing to false
      if (riderId) {
        fetch(`/riders/${riderId}/location`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ latitude: location?.latitude || 0, longitude: location?.longitude || 0, is_sharing: false }), // Send last known or default coords
        }).catch(err => console.error("위치 공유 비활성화 전송 실패:", err));
      }
    }

    return () => {
      if (watchId) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [riderId, isSharingLocation]); // Use isSharingLocation here

  return { location, error };
};

export default useGeolocation;
