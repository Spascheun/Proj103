import serverV3
import asyncio

HOST = "0.0.0.0" #localhost allowing external connections
PORT = 8080
MAIN_PAGE = "indexV2.html"
SUIVI_SERVER_URL = "http://proj103.r2.enst.fr"  # URL du serveur de suivi
SUIVI_SERVER_PORT = 80 # Port du serveur de suivi
SUIVI_UPDATE_INTERVAL = 1.0  # Intervalle en secondes pour l'envoi des mises à jour de suivi


class webServerAPI:
    def __init__(self):
        self.server = serverV3.webServer(
            host=HOST,
            port=PORT,
            main_page=MAIN_PAGE,
            suivi_server_url=SUIVI_SERVER_URL,
            suivi_server_port=SUIVI_SERVER_PORT,
            suivi_update_interval=SUIVI_UPDATE_INTERVAL,
            command_function=None  # Utilise la fonction de commande par défaut
        )
    async def start_server(self): return await self.server.start()
    async def close_server(self): await self.server.close()
