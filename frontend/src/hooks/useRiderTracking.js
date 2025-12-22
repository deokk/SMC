import { useState, useEffect, useRef } from 'react';

const useRiderTracking = (riderId) => {
  const [riderLocation, setRiderLocation] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    if (!riderId) {
      // 추적할 riderId가 없으면 연결 시도 안함
      if (ws.current) ws.current.close(); // 기존 연결 종료
      setRiderLocation(null); // 위치 정보 초기화
      setIsConnected(false);
      return;
    }

    // WebSocket URL 설정 (주소는 실제 환경에 맞게 조정 필요)
    // 로컬 개발: "ws://localhost:8000/ws/track/"
    // 배포 환경: "wss://your-domain.com/ws/track/"
    const wsUrl = `ws://localhost:8000/ws/track/${riderId}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log(`WebSocket connected for rider: ${riderId}`);
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const locationData = JSON.parse(event.data);
      setRiderLocation(locationData);
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // 컴포넌트 언마운트 시 WebSocket 연결 종료
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [riderId]); // riderId가 변경되면 WebSocket 재연결

  return { riderLocation, isConnected };
};

export default useRiderTracking;
