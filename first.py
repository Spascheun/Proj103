import http.server
from urllib.parse import urlparse
from urllib.parse import parse_qs
import threading
import time
import asyncio

# WebSocket server imports (optional dependency)
try:
	import websockets
	print("websockets package found, WebSocket server enabled")
except Exception:
	print("no websockets package found, WebSocket server will be disabled")
	websockets = None

# Shared container holding only the most recent command.
# Access protected by latest_cmd_lock.
latest_cmd = {'type': None, 'val': None}
latest_cmd_lock = threading.Lock()

# Classe permettant de gérer les requêtes HTTP. Elle étend la classe SimpleHTTPRequestHandler utilisée par le serveur HTTP
class GestionnaireRequetes(http.server.SimpleHTTPRequestHandler):
	def _set_headers(self, code):
		self.send_response(code)
		self.end_headers()

	# traitement d'une requete GET: ici seul "/index.html" (ou "/") est traité, toute autre requète répond 404
	# do_GET est une methode de la classe SimpleHTTPRequestHandler que nous surchargeons (remplaçons) ici
	def do_GET(self):
		if self.path == '/' or self.path == '' or self.path.startswith('/index'):
			try:
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()

				# Lire le contenu du fichier index.html
				with open('index.html', 'rb') as file:
					html_content = file.read()

				# Mettre le fichier lu comme corps de la réponse
				self.wfile.write(html_content)
			# erreur de lecture, on renvoi un code "server error" au client
			except:
				self._set_headers(500)
		else:
			self._set_headers(404)

	# traitement d'une requete POST: on stocke uniquement la dernière commande reçue et on répond immédiatement
	# do_POST est une methode de la classe SimpleHTTPRequestHandler que nous surchargeons (remplaçons) ici
	def do_POST(self):
		# dans cet exemple, on s'attend à recevoir une requete POST dont l'URL est "/commandes?type=STRING&val=INTEGER"
		if self.path.startswith('/commandes'):
			try:
				parsed_url = urlparse(self.path)
				params = parse_qs(parsed_url.query)
				cmd_type = params['type'][0]
				user_val = int(params['val'][0])
				# store latest command atomically and return quickly to avoid queueing
				with latest_cmd_lock:
					latest_cmd['type'] = cmd_type
					latest_cmd['val'] = user_val
				# respond immediately: the background worker will process the latest_cmd
				self._set_headers(200)
			except Exception as e:
				print('Failed to parse POST {} -> {}'.format(self.path, e))
				self._set_headers(400)
		else:
			print('Unknown request ' + str(self.path) )
			self._set_headers(400)


def command_worker(stop_event):
	"""Background thread that continuously checks for the latest command and processes only the most recent one.
	This avoids building a queue of commands when POST requests arrive faster than they can be processed.
	"""
	last_processed = (None, None)
	while not stop_event.is_set():
		# capture and clear the latest command atomically
		with latest_cmd_lock:
			cmd_type = latest_cmd.get('type')
			cmd_val = latest_cmd.get('val')
			# do not clear here; keep the command until processed to avoid losing it if worker is busy
		if cmd_type is not None:
			# if same as last processed, skip to avoid repeated processing
			if (cmd_type, cmd_val) != last_processed:
				# simulate actual processing (replace with real robot control code)
				try:
					print('Processing command: type={} val={}'.format(cmd_type, cmd_val))
					# place robot control invocation here; it's allowed to be slow
					# e.g., send to motor controller, etc.
					time.sleep(0.01)  # small simulated processing time
				except Exception as e:
					print('Error processing command: {}'.format(e))
				last_processed = (cmd_type, cmd_val)
		else:
			# no command: reset last_processed so a future identical command will be processed
			last_processed = (None, None)

		# sleep a short while to avoid busy loop; tune as needed
		#time.sleep(0.02)


# Créer un objet de la classe GestionnaireRequetes
mon_gestionnaire = GestionnaireRequetes

# créer un serveur HTTP sur le port 8080
PORT = 8080
httpd = http.server.HTTPServer(("", PORT), mon_gestionnaire)

# démarrer le worker en arrière-plan
stop_event = threading.Event()
worker_thread = threading.Thread(target=command_worker, args=(stop_event,), daemon=True)
worker_thread.start()


# --- WebSocket server (optional, minimal) ---------------------------------------
WS_PORT = 8765

async def ws_handler(websocket, path=None):
	"""Minimal WS handler: accept JSON messages and update latest_cmd.
	Some websockets versions call handler(websocket) others handler(websocket, path).
	"""
	import json
	print('WS client connected')
	try:
		async for message in websocket:
			try:
				data = json.loads(message)
				cmd_type = data.get('type')
				cmd_val = int(data.get('val', 0))
				with latest_cmd_lock:
					latest_cmd['type'] = cmd_type
					latest_cmd['val'] = cmd_val
			except Exception as e:
				# ignore malformed single messages but keep connection alive
				print('WS message error:', e)
	except Exception as e:
		print('WS connection closed or failed:', e)
	finally:
		print('WS client disconnected')


def start_ws_thread_minimal():
	if websockets is None:
		print('websockets package not installed: WebSocket server disabled')
		return None

	async def _serve():
		async with websockets.serve(ws_handler, '0.0.0.0', WS_PORT):
			print(f'WebSocket server listening on ws://0.0.0.0:{WS_PORT}')
			await asyncio.Future()  # run forever

	def _run():
		try:
			asyncio.run(_serve())
		except Exception as e:
			print('WebSocket server error (thread):', e)

	t = threading.Thread(target=_run, daemon=True)
	t.start()
	return t


ws_thread = None
if websockets is not None:
	ws_thread = start_ws_thread_minimal()

try:
	# on lance le serveur pour qu'il tourne jusqu'à l'arrêt du programme
	httpd.serve_forever()
except KeyboardInterrupt:
	print('Stopping server...')
	stop_event.set()
	httpd.shutdown()
	worker_thread.join()