import asyncio
import cv2
import av
from aiortc import VideoStreamTrack
from aiortc.mediastreams import MediaStreamError
import numpy as np


class videoSender(VideoStreamTrack):
	"""
	VideoStreamTrack qui lit depuis OpenCV (cv2.VideoCapture).
	Usage :
	  track = videoSender(source=0, width=640, height=480, fps=30)
	  pc.addTrack(track)
	Paramètres :
	  source : int (index de la caméra) ou cv2.VideoCapture déjà ouvert
	  width/height/fps : facultatifs (essayés d'être appliqués au capture si possible)
	"""
	def __init__(self, source, width=None, height=None, fps=30):
		super().__init__()  # initialise VideoStreamTrack
		
		self.capture = source
		
		# essayer d'appliquer les paramètres si fournis
		if width is not None:
			try: self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
			except Exception: pass
		if height is not None:
			try: self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
			except Exception: pass
		if fps is not None:
			try: self._capture.set(cv2.CAP_PROP_FPS, float(fps))
			except Exception: pass

		# boucle/executor
		self._loop = asyncio.get_event_loop()

	async def recv(self):
		"""
		Appelé par aiortc pour obtenir la prochaine frame.
		La lecture cv2 est faite via run_in_executor pour éviter de bloquer.
		"""

		# obtenir pts/time_base attendus par aiortc
		pts, time_base = await self.next_timestamp()

		# lire frame dans thread pool
		try:
			ret, frame = await self._loop.run_in_executor(None, self._capture.read)
		except Exception as e:
			# erreur de lecture -> lever pour terminer la piste
			raise MediaStreamError from e

		if not ret or frame is None:
			# retourner une frame noire si impossible de lire
			h = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
			w = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
			frame = (0 * (np.zeros((h, w, 3), dtype='uint8')))

		# convertir BGR (OpenCV) en av.VideoFrame en spécifiant format 'bgr24'
		video_frame = av.VideoFrame.from_ndarray(frame, format='bgr24')
		# définir pts/time_base fournis par next_timestamp
		video_frame.pts = pts
		video_frame.time_base = time_base
		return video_frame

