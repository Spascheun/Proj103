import API
import asyncio

async def main():
    api = API.webAPI()
    await api.start_server()
    await api.start_client()

asyncio.run(main())