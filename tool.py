import asyncio
from multiprocessing import SimpleQueue
import threading

class Queue:
    def __init__(self, loop=None):
        self.event = asyncio.Event()
        self.mp_q = SimpleQueue()
        self.latest_val = None
        self.running = True
        self.thread = threading.Thread(target=self.thread_target, daemon=True)
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self.thread.start()
    
    def thread_target(self):
        while self.running:
            item = self.mp_q.get()
            def _set():
                self.latest_val = item
                self.event.set()
            self.loop.call_soon_threadsafe(_set)


    