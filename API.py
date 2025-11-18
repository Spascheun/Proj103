import serverV3
import clientInServer
import asyncio
import multiprocessing
import threading


HOST = "0.0.0.0" #localhost allowing external connections
PORT = 8080
MAIN_PAGE = "indexV2.html"
JS_PATH = "javaScript/"
SUIVI_SERVER_URL = "http://proj103.r2.enst.fr"  # URL du serveur de suivi
SUIVI_SERVER_PORT = 80 # Port du serveur de suivi
SUIVI_UPDATE_INTERVAL = 1.0  # Intervalle en secondes pour l'envoi des mises à jour de suivi


#TODO: intégrer le contexte  de main_application pour acces aux fonction externes(get_position_function, command_function, etc.)
#TODO: intégrer le retour vidéo

class webAPI:
    def __init__(self,
            host=HOST,
            port=PORT,
            main_page=MAIN_PAGE,
            js_path=JS_PATH,
            suivi_server_url=SUIVI_SERVER_URL,
            suivi_server_port=SUIVI_SERVER_PORT,
            main_application = None,

        ):
            self.host = host
            self.port = port
            self.main_page = main_page
            self.suivi_server_url = suivi_server_url
            self.suivi_server_port = suivi_server_port
            self.server_process = None
            self.loop = None
            self.client = None
            self.running = False
            self.client_running = False
            self.server_running = False
            self.main_application = main_application
            self.command_queue = None
            self.toggle_queue = None
            self.worker = asyncio.gather(self.command_worker(), self.toggle_worker())

    def start(self):
        if self.running: 
            print("webAPI is already running")
            return
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop_init, daemon=False)
        self.thread.start()
        self.running = True
        asyncio.run_coroutine_threadsafe(self.worker, self.loop)
        self.start_server()
        self.start_client()


    def loop_init(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        finally:
            print("Closing webAPI...")
            if self.loop.is_running():
                self.loop.stop()
            self.loop.close()
            self.loop = None
            asyncio.run(self._close_client())
            self.close_server()
            print("webAPI closed")

    async def command_worker(self):
        while self.running:
            command = await self.command_queue.get()
            self.main_application.movement.set_joystick_state(command['x'], command['y'])
        
    async def toggle_worker(self):
        while self.running:
            toggle = await self.toggle_queue.get()
            self.main_application.movement.toggle_mode()

    def _ensure_loop(self):
        if self.loop is not None and self.loop.is_running():
            return True
        else : return False

    def _ensure_client(self):
        if not self._ensure_loop():
            print("Event loop not initialized yet. Wait a moment and try again.")
            return False
        if self.client is None or not self.client_running:
            print("Client is not running")
            return False
        return True

    def start_server(self):  
        if not self.running:
            print("webAPI is not running. Start webAPI before starting the server.")
            return
        if self.server_running and self.server_process is not None and self.server_process.is_alive():
            print("Web server process is already running")
            return
        print("Starting web server process")
        # ensure we have a command_queue to communicate with the child
        if self.command_queue is None:
            self.command_queue = multiprocessing.Queue()
        if self.toggle_queue is None:
            self.toggle_queue = multiprocessing.Queue()
        self.server_process = multiprocessing.Process(target=serverV3.new_web_server_process, args=(self.export_config(), self.command_queue, self.toggle_queue), daemon=False)
        self.server_process.start()
        self.server_running = True
        print("Web server process started")

    async def _start_client(self):
        if self.client_running or self.client is not None:
            print("Client is already running")
            return
        self.client_running = True
        self.client = clientInServer.webClient(
                self.suivi_server_url,
                self.suivi_server_port,
            )
            
    def start_client(self):
        if self.running is False or self.thread is None or self.thread.is_alive() is False:
            print("webAPI is not running. Start webAPI before starting the client.")
            return
        if not self._ensure_loop():
            print("Event loop not initialized yet. Wait a moment and try again.")
            return
        asyncio.run_coroutine_threadsafe(self._start_client(), self.loop).result()


    def close_server(self):
         if self.server_process.is_alive():
            print("Terminating web server process")
            self.server_process.terminate()
            self.server_process.join()
            self.server_process.close()
            self.server_process = None
            self.server_running = False
            print("Web server process terminated")
        

    def close_client(self):
        if not self._ensure_loop():
            print("Event loop not initialized yet. Wait a moment and try again.")
            return
        if not self.client_running :
            print("Client is not running")
            return
        asyncio.run_coroutine_threadsafe(self.client.close(), self.loop).result()
        self.client_running = False

    async def _close_client(self):
        if not self.client_running :
            print("Client is not running")
            return
        await self.client.close()
        self.client_running = False
        self.client = None
        

    def close(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()
        self.running = False

    def export_config(self):
        """Return a plain dict of the API configuration safe to pass to a child process. """
        return {
            "host": self.host,
            "port": self.port,
            "main_page": self.main_page,
            "js_path": self.js_path
        }

    # --- Proxy methods: schedule clientInServer.webClient coroutines on server loop ---
    # Each method returns the concurrent.futures.Future returned by
    # asyncio.run_coroutine_threadsafe(...). Callers may call .result(timeout)
    # or convert to an awaitable with asyncio.wrap_future() if needed.

    def start_update_suivi(self, get_position_function, suivi_update_interval = SUIVI_UPDATE_INTERVAL  ,tid = None):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.update_suivi(get_position_function, suivi_update_interval, tid), self.loop)

    def stop_update_suivi(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.stop_update_suivi(), self.loop)
    def get_flags(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.get_flags(), self.loop)

    def capture_flag(self, mid, msec, minner, tid=None, wait=True):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.capture_flag(mid, msec, minner, tid, wait), self.loop)
    def get_race_status(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.get_race_status(), self.loop)

    def write_register(self, rid, val, tid=None):
        if not self._ensure_client(): return   
        return asyncio.run_coroutine_threadsafe(self.client.write_register(rid, val, tid), self.loop)
    
    def read_register(self, rid, team=None):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.read_register(rid, team), self.loop)

    def launch_race(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.launch_race(), self.loop)
    
    def stop_race(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.stop_race(), self.loop)

    def select_flag_pattern(self, n):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.select_flag_pattern(n), self.loop)
    
    def get_flag_pattern(self):
        if not self._ensure_client(): return
        return asyncio.run_coroutine_threadsafe(self.client.get_flag_pattern(), self.loop)
        