import asyncio
import API as webAPI

async def main():
    web_api = webAPI.webAPI()
    await web_api.start_server()
    await web_api.start_client()

if __name__ == "__main__":
    asyncio.run(main())