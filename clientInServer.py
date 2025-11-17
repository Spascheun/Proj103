import aiohttp as web
import warnings
import asyncio
import json


class webClient:
    def __init__(self, suivi_server_url, suivi_server_port):
        self.session = web.ClientSession()
        self.suivi_server_url = suivi_server_url
        self.suivi_server_port = suivi_server_port
        self.send_position = True


    async def close(self):
        print("Closing web client")
        self.send_position = False
        await self.session.close()
        print("Web client closed")
        
    

    async def http_status_handler(self, status_code, context, response_text=None):
        match status_code:
            case 200:
                print(f"{context} succeeded")
                return True 
            case 400:
                warnings.warn(f"Bad request when {context}: {response_text}")
                return False
            case 401:
                warnings.warn(f"Unauthorized access when {context}")
                return False
            case 404:
                warnings.warn(f"API command not recognized when {context}")
                return False
            case 500:
                warnings.warn(f"Internal server error when {context}")
                return False
            case 503:
                warnings.warn(f"{context} command received but no exam is running")
                return False
            case _:
                warnings.warn(f"Unexpected status code {status_code} when {context}")
                return False

    async def start_update_suivi(self, get_position_function, suivi_update_interval, tid = None):
        t = "" if tid is None else f"&t={tid}"
        print(f"Starting location updates every {suivi_update_interval} seconds to {self.suivi_server_url}:{self.suivi_server_port} {"" if tid is None else f"as team {tid}"}")
        while self.send_position:
            x, y = await get_position_function()
            async with self.session.post(f"{self.suivi_server_url}/api/pos?x={x}&y={y}{t}:{self.suivi_server_port}") as resp:
                self.http_status_handler(await resp.status, "Position update", await resp.text())
            await asyncio.sleep(suivi_update_interval)
        print("Stopping location updates")

    async def stop_update_suivi(self):
        self.send_position = False

    async def get_flags(self):
        async with self.session.get(f"{self.suivi_server_url}/api/list:{self.suivi_server_port}") as resp:
            body = await resp.text()
            if self.http_status_handler(await resp.status, "Flags retrieval", body):
                return json.loads(body)
            else:
                return None
        
    async def capture_flag(self, mid, msec, minner, tid=None, wait=True):
        t = "" if tid is None else f"&t={tid}"
        async with self.session.post(f"{self.suivi_server_url}/api/marker?id={mid}&sector={msec}&inner={minner}{t}:{self.suivi_server_port}") as resp:
            if wait:
                return self.http_status_handler(await resp.status, "Flag capture", await resp.text())
            else: 
                return None

    async def get_race_status(self):
        async with self.session.get(f"{self.suivi_server_url}/api/status:{self.suivi_server_port}") as resp:
            body =  await resp.text()
            if self.http_status_handler(await resp.status, "Race status retrieval", body):
                return json.loads(body)
            else:
                return None

    async def write_register(self, rid, val, tid = None):
        t = "" if tid is None else f"&t={tid}"
        async with self.session.post(f"{self.suivi_server_url}/api/udta?idx={rid}&all={val}{t}:{self.suivi_server_port}") as resp:
            return self.http_status_handler(await resp.status, "Register write", await resp.text())

    async def read_register(self, rid, team = None):
        t = "" if team is None else f"&t={team}"
        async with self.session.get(f"{self.suivi_server_url}/api/udta?idx={rid}{t}:{self.suivi_server_port}") as resp:
            body = await resp.text()
            if self.http_status_handler(await resp.status, "Register read", body):
                return json.loads(body)
            else:
                return None

    async def launch_race(self):
        async with self.session.post(f"{self.suivi_server_url}/api/start:{self.suivi_server_port}") as resp:
            return self.http_status_handler(await resp.status, "Race launch", await resp.text())

    async def stop_race(self):
        async with self.session.post(f"{self.suivi_server_url}/api/stop:{self.suivi_server_port}") as resp:
            return self.http_status_handler(await resp.status, "Race stop", await resp.text())

    async def select_flag_pattern(self, n):
        async with self.session.post(f"{self.suivi_server_url}/api/pattern?idx={n}:{self.suivi_server_port}") as resp:
            return self.http_status_handler(await resp.status, "Flag pattern selection", await resp.text())

    async def get_flag_pattern(self):
        async with self.session.get(f"{self.suivi_server_url}/api/pattern:{self.suivi_server_port}") as resp:
            body = await resp.text()
            if self.http_status_handler(await resp.status, "Flag pattern retrieval", body):
                return json.loads(body)
            else:
                return None
        

