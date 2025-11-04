import asyncio
import json
from aiohttp import web
import aiortc as rtc
import os
from typing import Optional

HOST = "0.0.0.0"
PORT = 8080
MAIN_PAGE = "indexV2.html"

pc = {}

# shared container holding only the most recent command (type/val)
latest_cmd = {'type': None, 'val': None}
latest_cmd_lock = asyncio.Lock()

# background worker task handle (stored in app)
CMD_WORKER_INTERVAL = 0.02  # seconds, tune as needed

async def command_worker_task(app):
    """Async worker that processes only the latest command (no queue)."""
    last_processed = (None, None)
    try:
        while True:
            async with latest_cmd_lock:
                cmd_type = latest_cmd.get('type')
                cmd_val = latest_cmd.get('val')
            if cmd_type is not None and (cmd_type, cmd_val) != last_processed:
                try:
                    # Simulate processing; replace with your real handling code.
                    print(f'Processing command: type={cmd_type} val={cmd_val}')
                    await asyncio.sleep(0.01)  # simulate I/O/actuation
                except Exception as e:
                    print('Error processing command:', e)
                last_processed = (cmd_type, cmd_val)
            elif cmd_type is None:
                last_processed = (None, None)

            await asyncio.sleep(CMD_WORKER_INTERVAL)
    except asyncio.CancelledError:
        # graceful exit on shutdown
        return

async def ws_handler(request: web.Request):
    raw_msg = await request.json()
    return command(raw_msg[0], raw_msg[1])


async def offer_command(request : web.Request) -> web.Response:
    params = await request.json()
    offer = rtc.RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    peer_connection = rtc.RTCPeerConnection()
    pc["command_peer"] = peer_connection

    # handle incoming DataChannel from the client
    @peer_connection.on("datachannel")
    def on_datachannel(channel):
        print("DataChannel created:", channel.label)

        @channel.on("message")
        def on_message(message):
            try:
                # expect JSON like {"type":"cmd","val":123}
                if isinstance(message, (bytes, bytearray)):
                    message = message.decode('utf-8')
                data = json.loads(message)
                cmd_type = data.get('type')
                cmd_val = int(data.get('val', 0))
                # update latest command atomically
                async def _update():
                    async with latest_cmd_lock:
                        latest_cmd['type'] = cmd_type
                        latest_cmd['val'] = cmd_val
                asyncio.ensure_future(_update())
                # optional: send ack
                try:
                    channel.send(json.dumps({'status': 'ok', 'type': cmd_type, 'val': cmd_val}))
                except Exception:
                    pass
                print('DC parsed command:', cmd_type, cmd_val)
            except Exception as e:
                print('DC message error:', e)

    await peer_connection.setRemoteDescription(offer)
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)
    print("Created WebRTC command peer connection, sending answer")

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
    # start command worker background task
    task = asyncio.create_task(command_worker_task(app))
    app['cmd_worker_task'] = task


def command(x,y) :
    print(f"Command {x,y} treated")
    return True

if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/offer_command", offer_command)
    # websocket endpoint for commands (fallback or alternate)
    app.router.add_get("/ws", ws_handler)
    # serve index at root as well
    app.router.add_get("/", get_main_page_handler)
    app.router.add_get("/{MAIN_PAGE}", get_main_page_handler)
    app.on_startup.append(on_startup)
    web.run_app(app, host=HOST, port=PORT)