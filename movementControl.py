from multiprocessing import Process, Queue
import asyncio
import control_moteur as moteur

class controlExecutor:
    def __init__(self, command_queue : Queue):
        self.command_queue = command_queue
        self.process = Process(target=self.run, args=(command_queue,), daemon=True)
        self.process.start()
    
    def push_command(self, command):
        self.command_queue.put(command)

    def run(self, command_queue : Queue):
        async def control_loop():
            running = True
            while running:
                _command = await command_queue.get()
                moteur.joystick(_command)
        
        asyncio.run(control_loop())