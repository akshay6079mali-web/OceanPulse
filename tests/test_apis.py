import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as c:
        try:
            r1 = await c.get('http://127.0.0.1:8000/api/v1/slicks')
            print('Slicks:', len(r1.json()))
        except Exception as e:
            print("Slicks error:", e)
        
        try:
            r2 = await c.get('http://127.0.0.1:8000/api/v1/sar/passes')
            print('SAR:', len(r2.json()))
        except Exception as e:
            print("SAR error:", e)

if __name__ == "__main__":
    asyncio.run(test())
