Robot control demo

This small project runs a minimal Python HTTP server (`first.py`) serving `index.html`.
It also supports a WebSocket server (optional) on port 8765 for low-latency joystick control.

Requirements
- Python 3.7+
- (optional) `websockets` package for WebSocket support

Install optional dependency:

```powershell
py -m pip install websockets
```

Run the server:

```powershell
py .\first.py
```

Open the UI in your browser:

http://localhost:8080/

Behavior
- If `websockets` is installed, the client (`index.html`) will attempt to connect to ws://localhost:8765 and send joystick messages over WS.
- If WS is not available, the client falls back to POST requests to `/commandes`.

Notes
- For production use, secure WebSocket (wss://) and proper authentication are recommended.
