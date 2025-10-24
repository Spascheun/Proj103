import asyncio
import json
from aiohttp import web
import aiortc as rtc

HOST = "localhost"
PORT = 8080
MAIN_PAGE = "index.html"


pc = {}

async def offer_command(request : web.Request) -> web.Response:
    params = await request.json()
    offer = rtc.RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    peer_connection = rtc.RTCPeerConnection()
    pc["command_peer"] = peer_connection

    @peer_connection.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        ICEState = peer_connection.iceConnectionState
        print("ICE connection state is %s" % ICEState)
        if ICEState == "failed":
            await peer_connection.close()
            del pc["command_peer"]

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

async def on_startup(app):
    print(f"\033[92mServer started at http://{HOST}:{PORT}", flush=True)
    print(f"Main page at http://{HOST}:{PORT}/{MAIN_PAGE} \033[0m", flush=True)

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/offer_command", offer_command)
    app.router.add_get("/{MAIN_PAGE}", get_main_page_handler)
    app.on_startup.append(on_startup)
    web.run_app(app, host=HOST, port=PORT)