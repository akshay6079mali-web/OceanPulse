import asyncio, websockets, requests
async def test():
    token = requests.post('http://127.0.0.1:8000/token', data={'username':'admin', 'password':'password123'}).json()['access_token']
    async with websockets.connect(f'ws://127.0.0.1:8000/api/v1/stream/ais?token={token}') as ws:
        print(await ws.recv())
        print(await ws.recv())
asyncio.run(test())
