import asyncio
from aiortc import VideoStreamTrack

class videoSender(VideoStreamTrack):

    def __init__(self):
        super().__init__()  # Initialize the base class

    async def recv(self):
        #Source function for video stream by WebRTC
        pass