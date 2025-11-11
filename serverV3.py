import asyncio
import json
from aiohttp import web
import aiortc as rtc
import clientInServer as cis
import threading

pc = {}

class webServer:
    def __init__(self, host, port, main_page, command_function=None):
        self.host = host
        self.port = port
        self.main_page = main_page
        self.command = command_function if command_function is not None else lambda cmd: print("Command received:", cmd)
        self.app = web.Application()
        self.app.router.add_post("/rtcOffer_command", self.rtcOffer_command)
        self.app.router.add_get("/", self.get_main_page_handler)
        self.app.router.add_get("/javaScript/main.js", self.get_main_js_handler)
        self.app.router.add_get("/javaScript/WebRTCClient.js", self.get_web_rtc_client_js_handler)
        self.app.router.add_get("/javaScript/WebSocketClient.js", self.get_web_socket_client_js_handler)
        self.app.add_routes([web.get('/ws', self.ws_command)])
        self.runner = web.AppRunner(self.app)

    def _ensure_loop(self):
        if not hasattr(self, 'loop'):
            raise RuntimeError("Server loop not started. Call start() before using client proxy methods.")



    async def thread_init(self):
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()
        print(f"\033[92mServer started at http://{self.host}:{self.port}", flush=True)
        print(f"Main page at http://{self.host}:{self.port} \033[0m", flush=True)

        
    async def thread_loop_init(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def start(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.thread_loop_init, args=(self.loop,), daemon=True)
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

    