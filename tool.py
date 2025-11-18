import asyncio
from multiprocessing import SimpleQueue
import threading

class Queue:
    def __init__(self, loop=None):
        self.async_q = asyncio.Queue()
        self.mp_q = SimpleQueue()
        self.running = True
        self.thread = threading.Thread(target=self.thread_target, daemon=True)
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self.thread.start()
    
    def thread_target(self):
        while self.running:
            self.loop.call_soon_threadsafe(self.async_q.put_nowait, self.mp_q.get())


    