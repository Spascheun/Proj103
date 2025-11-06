import asyncio
import json
from aiohttp import web
import aiortc as rtc

HOST = "0.0.0.0" #localhost allowing external connections
PORT = 8080
MAIN_PAGE = "indexV2.html"


pc = {}

def command(cmd : dict):
    print("Command received:", cmd)
    # Traiter la commande reçue 

async def ws_command(request : web.Request) -> web.Response:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    pc["command_ws"] = ws
    print('websocket connection established')

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                command(json.loads(msg.data))
            except Exception:
                print("Failed to treat message as command")
                pass
        elif msg.type == web.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    del pc["command_ws"]
    print('websocket connection closed')
    return ws

async def rtcOffer_command(request : web.Request) -> web.Response:
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
                command(json.loads(message))
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

async def get_main_page_handler(request : web.Request) -> web.Response:
    return web.FileResponse(MAIN_PAGE)

async def get_main_js_handler(request : web.Request) -> web.Response:
    return web.FileResponse("javaScript/main.js")

async def get_web_rtc_client_js_handler(request : web.Request) -> web.Response:
    return web.FileResponse("javaScript/WebRTCClient.js")

async def get_web_socket_client_js_handler(request : web.Request) -> web.Response:
    return web.FileResponse("javaScript/WebSocketClient.js")

async def on_startup(app):
    print(f"\033[92mServer started at http://{HOST}:{PORT}", flush=True)
    print(f"Main page at http://{HOST}:{PORT} \033[0m", flush=True)

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/rtcOffer_command", rtcOffer_command)
    app.router.add_get("/", get_main_page_handler)
    app.router.add_get("/javaScript/main.js", get_main_js_handler)
    app.router.add_get("/javaScript/WebRTCClient.js", get_web_rtc_client_js_handler)
    app.router.add_get("/javaScript/WebSocketClient.js", get_web_socket_client_js_handler)
    app.add_routes([web.get('/ws', ws_command)])
    app.on_startup.append(on_startup)
    web.run_app(app, host=HOST, port=PORT)