import asyncio
import json
from aiohttp import web
import aiortc as rtc
import clientInServer as cis
import threading

pc = {}

class webServer:
    def __init__(self, host, port, main_page, suivi_server_url, suivi_server_port, suivi_update_interval, command_function=None):
        self.client = cis.webClient(suivi_server_url, suivi_server_port, suivi_update_interval)
        self.host = host
        self.port = port
        self.main_page = main_page
        self.command = command_function if command_function is not None else lambda cmd: print("Command received:", cmd)


    async def close(self):
        """Close the underlying client on the server event loop.

        This schedules the client's close coroutine on the server's secondary loop
        and awaits its completion. If the server loop isn't started yet, fall back
        to calling the client's close() directly.
        """
        if hasattr(self, 'loop'):
            fut = asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
            # wrap the concurrent.futures.Future so we can await it
            return await asyncio.wrap_future(fut)
        else:
            await self.client.close()

    def _ensure_loop(self):
        if not hasattr(self, 'loop'):
            raise RuntimeError("Server loop not started. Call start() before using client proxy methods.")



    async def thread_init(self):
        self.app = web.Application()
        self.app.router.add_post("/rtcOffer_command", self.rtcOffer_command)
        self.app.router.add_get("/", self.get_main_page_handler)
        self.app.router.add_get("/javaScript/main.js", self.get_main_js_handler)
        self.app.router.add_get("/javaScript/WebRTCClient.js", self.get_web_rtc_client_js_handler)
        self.app.router.add_get("/javaScript/WebSocketClient.js", self.get_web_socket_client_js_handler)
        self.app.add_routes([web.get('/ws', self.ws_command)])
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        print(f"\033[92mServer started at http://{self.host}:{self.port}", flush=True)
        print(f"Main page at http://{self.host}:{self.port} \033[0m", flush=True)

        
    async def thread_loop_init(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def start(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.thread_loop_init, daemon=True)
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self.thread_init(), self.loop).result()

    async def ws_command(self, request : web.Request) -> web.Response:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        pc["command_ws"] = ws
        print('websocket connection established')

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    self.command(json.loads(msg.data))
                except Exception:
                    print("Failed to treat message as command")
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                    ws.exception())

        del pc["command_ws"]
        print('websocket connection closed')
        return ws

    async def rtcOffer_command(self, request : web.Request) -> web.Response:
        params = await request.json()
        offer = rtc.RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        peer_connection = rtc.RTCPeerConnection()
        pc["command_peer"] = peer_connection


        @peer_connection.on("datachannel")
        def on_datachannel(channel):
            print("DataChannel received:", channel.label)
            pc["command_dc"] = channel

            @channel.on("open")
            def on_open():
                print("DataChannel opened:", channel.label)

            @channel.on("message")
            def on_message(message):
                try:
                    self.command(json.loads(message))
                except Exception:
                    print("Failed to treat message as command")
                    pass

        @peer_connection.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            ICEState = peer_connection.iceConnectionState
            print("ICE connection state is %s" % ICEState)
            match ICEState:
                case "failed":
                    await peer_connection.close()
                    del pc["command_peer"]
                case "completed":
                    print("WebRTC connection established")
                case "closed":
                    print("WebRTC connection closed")

        await peer_connection.setRemoteDescription(offer)
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)
        

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": peer_connection.localDescription.sdp, "type": peer_connection.localDescription.type}
            ),
        )

    async def get_main_page_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse(self.main_page)

    async def get_main_js_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse("javaScript/main.js")

    async def get_web_rtc_client_js_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse("javaScript/WebRTCClient.js")

    async def get_web_socket_client_js_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse("javaScript/WebSocketClient.js")

    # --- Proxy methods: schedule clientInServer.webClient coroutines on server loop ---
    # Each method returns the concurrent.futures.Future returned by
    # asyncio.run_coroutine_threadsafe(...). Callers may call .result(timeout)
    # or convert to an awaitable with asyncio.wrap_future() if needed.

    def update_suivi(self, get_position_function, tid=None):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.update_suivi(get_position_function, tid), self.loop)

    def get_flags(self):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_flags(), self.loop)

    def capture_flag(self, mid, msec, minner, tid=None, wait=True):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.capture_flag(mid, msec, minner, tid, wait), self.loop)

    def get_race_status(self):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_race_status(), self.loop)

    def write_register(self, rid, val, tid=None):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.write_register(rid, val, tid), self.loop)

    def read_register(self, rid, team=None):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.read_register(rid, team), self.loop)

    def launch_race(self):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.launch_race(), self.loop)

    def stop_race(self):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.stop_race(), self.loop)

    def select_flag_pattern(self, n):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.select_flag_pattern(n), self.loop)

    def get_flag_pattern(self):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_flag_pattern(), self.loop)