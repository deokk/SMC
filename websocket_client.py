# websocket_client.py
import asyncio
import websockets
import json

async def test_websocket_client(rider_id: str):
    # FastAPI가 8000 포트에서 실행 중이라고 가정합니다. 필요에 따라 변경하세요.
    uri = f"ws://localhost:8000/ws/track/{rider_id}" 
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to WebSocket for rider {rider_id}. Waiting for updates...")
            try:
                while True:
                    message = await websocket.recv()
                    print(f"Received update for {rider_id}: {message}")
            except websockets.exceptions.ConnectionClosedOK:
                print(f"WebSocket connection closed for rider {rider_id}.")
            except Exception as e:
                print(f"An error occurred during WebSocket communication: {e}")
    except ConnectionRefusedError:
        print(f"Connection refused. Is the FastAPI server running at {uri.split('/ws')[0]}?")
    except Exception as e:
        print(f"Could not connect to WebSocket: {e}")

if __name__ == "__main__":
    # 테스트할 라이더 ID를 지정하세요. POST 요청으로 업데이트하는 ID와 동일해야 합니다.
    test_rider_id = "test_rider_123" 
    asyncio.run(test_websocket_client(test_rider_id))
