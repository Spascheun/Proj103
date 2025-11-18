import API
import sys
import signal

def signal_handler(sig, frame):
    print("Signal received, closing program...")
    api.close()
    sys.exit(0)

if __name__ == "__main__":
    api = API.webAPI()
    signal.signal(signal.SIGINT, signal_handler) 
    signal.signal(signal.SIGTERM, signal_handler)
    api.start()
    while True:
        pass