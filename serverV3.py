import asyncio
import json
from aiohttp import web
import aiortc as rtc
import clientInServer as cis
import threading


class webServer:
    def __init__(self, host, port, main_page, command_function=None):
        self.host = host
        self.port = port
        self.main_page = main_page
        self.command = command_function if command_function is not None else lambda cmd: print("Command received:", cmd)


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


    async def thread_init(self):
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()
        print(f"\033[92mServer started at http://{self.host}:{self.port}", flush=True)
        print(f"Main page at http://{self.host}:{self.port} \033[0m", flush=True)

        
    def thread_loop_init(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def start(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.thread_loop_init, args=(self.loop,), daemon=True)
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self.thread_init(), self.loop).result()


    async def ws_command(self, request : web.Request) -> web.Response:
        self.ws = web.WebSocketResponse()
        await self.ws.prepare(request)

        print('websocket connection established')

        async for msg in self.ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    self.command(json.loads(msg.data))
                except Exception:
                    print("Failed to treat message as command")
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                print('ws connection closed with exception %s' %
                    self.ws.exception())

        del self.ws
        print('websocket connection closed')
        return self.ws

    async def toggle_commands(self):
        pass

    async def rtcOffer_command(self, request : web.Request) -> web.Response:
        params = await request.json()
        offer = rtc.RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        self.pc = rtc.RTCPeerConnection()


        @self.pc.on("datachannel")
        def on_datachannel(channel):
            print("DataChannel received:", channel.label)
            self.dc = channel

            @channel.on("open")
            def on_open():
                print("DataChannel opened:", channel.label)

            @channel.on("message")
            def on_message(message):
                try:
                    msg = json.loads(message)
                    match msg['type']:
                        case "command":
                            self.command(msg['x'], msg['y'])
                        case "toggle_commands":
                            self.toggle_commands()
                except Exception:
                    print("Failed to treat message as command")
                    pass

        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            ICEState = self.pc.iceConnectionState
            print("ICE connection state is %s" % ICEState)
            match ICEState:
                case "failed":
                    await self.pc.close()
                    del self.pc
                case "completed":
                    print("WebRTC connection established")
                case "closed":
                    print("WebRTC connection closed")

        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type}
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

    