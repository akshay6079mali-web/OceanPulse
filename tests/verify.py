import httpx
import websockets
import asyncio
import json

async def main():
    # 1. Authenticate
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/token",
            data={"username": "admin", "password": "password123"}
        )
        token = response.json()["access_token"]
        print(f"Token received.")

        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get slicks
        res_slicks = await client.get("http://127.0.0.1:8000/api/v1/slicks", headers=headers)
        slicks = res_slicks.json()
        print(f"Slicks:")
        for s in slicks:
            print(f"Lon: {s['coordinates']['lon']} <= 72.68, timestamp: {s['timestamp']}")
            
        # 3. Get incois/forecast
        res_incois = await client.get("http://127.0.0.1:8000/api/v1/incois/forecast", headers=headers)
        forecast = res_incois.json()
        print(f"INCOIS Forecast: Wind Speed {forecast.get('wind_speed_knots')}, Vectors Count {len(forecast.get('vectors', []))}")
        
    # 4. Websocket
    print("Connecting to websocket...")
    async with websockets.connect(f"ws://127.0.0.1:8000/api/v1/stream/ais?token={token}") as ws:
        for _ in range(5):
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"WS Frame: MMSI {data['mmsi']} Lon {data['lon']} <= 72.68")

if __name__ == "__main__":
    asyncio.run(main())
