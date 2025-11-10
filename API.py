import serverV3
import clientInServer
import asyncio

HOST = "0.0.0.0" #localhost allowing external connections
PORT = 8080
MAIN_PAGE = "indexV2.html"
SUIVI_SERVER_URL = "http://proj103.r2.enst.fr"  # URL du serveur de suivi
SUIVI_SERVER_PORT = 80 # Port du serveur de suivi
SUIVI_UPDATE_INTERVAL = 1.0  # Intervalle en secondes pour l'envoi des mises à jour de suivi


#TODO: intégrer le contexte  de main_application pour acces aux fonction externes(get_position_function, command_function, etc.)
#TODO: intégrer le retour vidéo
#TODO: gérer l'arrêt propre des boucles d'event asyncio et des threads associés

class webAPI:
    def __init__(self,
            host=HOST,
            port=PORT,
            main_page=MAIN_PAGE,
            suivi_server_url=SUIVI_SERVER_URL,
            suivi_server_port=SUIVI_SERVER_PORT,
            suivi_update_interval=SUIVI_UPDATE_INTERVAL,
            command_function=None  # Utilise la fonction de commande par défaut
        ):
            self.server = serverV3.webServer(
                host,
                port,
                main_page,
                command_function # Utilise la fonction de commande par défaut
            )
            self.client = clientInServer.webClient(
                suivi_server_url,
                suivi_server_port,
                suivi_update_interval
            )

    async def start_server(self): return await self.server.start()
    async def close_server(self): await self.server.close()

    async def start_client(self): return await self.client.start()
    async def close_client(self): await self.client.close()

    # --- Proxy methods: schedule clientInServer.webClient coroutines on server loop ---
    # Each method returns the concurrent.futures.Future returned by
    # asyncio.run_coroutine_threadsafe(...). Callers may call .result(timeout)
    # or convert to an awaitable with asyncio.wrap_future() if needed.

    def update_suivi(self, get_position_function, tid=None):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.update_suivi(get_position_function, tid), self.client.loop)

    def get_flags(self):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_flags(), self.client.loop)

    def capture_flag(self, mid, msec, minner, tid=None, wait=True):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.capture_flag(mid, msec, minner, tid, wait), self.client.loop)

    def get_race_status(self):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_race_status(), self.client.loop)

    def write_register(self, rid, val, tid=None):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.write_register(rid, val, tid), self.client.loop)

    def read_register(self, rid, team=None):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.read_register(rid, team), self.client.loop)

    def launch_race(self):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.launch_race(), self.client.loop)

    def stop_race(self):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.stop_race(), self.client.loop)

    def select_flag_pattern(self, n):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.select_flag_pattern(n), self.client.loop)

    def get_flag_pattern(self):
        self.client._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self.client.get_flag_pattern(), self.client.loop)
