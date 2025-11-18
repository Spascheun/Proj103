import json
from aiohttp import web
import aiortc as rtc
from multiprocessing import SimpleQueue
import warnings


def new_web_server_process(cfg : dict, command_queue : SimpleQueue, toggle_queue : SimpleQueue) -> None:
    '''Start a web server in a new process using the plain config dict.

    `cfg` is expected to be a dict with keys: host, port, main_page, ...
    `command_queue` is a multiprocessing.SimpleQueue used for parent-child IPC.
    '''
    print("initializing web server process")
    server = webServer(cfg["host"], cfg["port"], cfg["main_page"], cfg["js_path"], command_queue, toggle_queue)
    server.run() 

class webServer:
    def __init__(self, host : str, port : int, main_page : str, js_path : str, command_queue : SimpleQueue, toggle_queue : SimpleQueue):
        self.host = host
        self.port = port
        self.main_page = main_page
        self.js_path = js_path
        self.command_queue = command_queue
        self.toggle_queue = toggle_queue
        self.app = web.Application()
        self.app.router.add_post("/rtcOffer_command", self.rtcOffer_command)
        self.app.router.add_get("/", self.get_main_page_handler)
        self.app.router.add_get("/javaScript/main.js", self.get_main_js_handler)
        self.app.router.add_get("/javaScript/WebRTCClient.js", self.get_web_rtc_client_js_handler)
        self.app.router.add_get("/javaScript/WebSocketClient.js", self.get_web_socket_client_js_handler)
        self.app.add_routes([web.get('/ws', self.ws_command)])

    def command(self, cmd : dict):
        """Handle a command received from a client."""
        #print("Command received:", cmd)
        if self.command_queue is not None:
            self.command_queue.put(cmd)
        else:
            warnings.warn("No command queue defined; cannot forward command")
            

    def run(self):
        print(f"\033[92mServer starting at http://{self.host}:{self.port}", flush=True)
        print(f"Main page at http://{self.host}:{self.port} \033[0m", flush=True)
        web.run_app(self.app, host=self.host, port=self.port)
        print("Web server stopped")


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
        #print("Toggling commands")
        if self.toggle_queue is not None:
            self.toggle_queue.put(True)
        else:
            warnings.warn("No toggle queue defined; cannot toggle commands")

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
                            self.command((msg['x'], msg['y']))
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
        print("Serving main.js")
        return web.FileResponse(f"{self.js_path}main.js")

    async def get_web_rtc_client_js_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse(f"{self.js_path}WebRTCClient.js")

    async def get_web_socket_client_js_handler(self, request : web.Request) -> web.Response:
        return web.FileResponse(f"{self.js_path}WebSocketClient.js")

    