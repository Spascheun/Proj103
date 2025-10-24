/* Ébauche : crée une RTCPeerConnection, envoie l'offer au serveur et gère les ICE candidates.
   Usage simple : window.startWebRTC({offerUrl:'/webrtc/offer', iceUrl:'/webrtc/ice', useMedia:true})
*/

(function () {
	// Configuration ICE (STUN public, adapter si nécessaire)
	const DEFAULT_CONFIG = {iceServers: [{ }]};

	// Envoie JSON au serveur et retourne la réponse JSON
	async function postJson(url, body) {
		const res = await fetch(url, {
			method: 'POST',
			body: JSON.stringify(body)
		});
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		return await res.json();
	}

	// Point d'entrée : démarre la négociation et retourne l'objet peer et dataChannel
	async function startWebRTC(options = {}) {
		const offerUrl = options.offerUrl || '/offer';
		const pc = new RTCPeerConnection(options.rtcConfig || DEFAULT_CONFIG);

		// Data channel pour commandes
		const dc = pc.createDataChannel('commands');

		dc.onopen = () => {
			console.log('DataChannel open');
		};
		dc.onmessage = (ev) => console.log('DataChannel msg:', ev.data);
		dc.onerror = (e) => console.warn('DataChannel error', e);
		dc.onclose = () => console.log('DataChannel closed');

		// sendCommand: envoie un objet (ou string) sur le dataChannel, bufferise si nécessaire
		function sendCommand(x,y) {
			if (dc.readyState === 'open') {
				try {
					dc.send({x,y});
					return true;
				} catch (e) {
					return false;
				}
			}
		}

		// Create offer
		const offer = await pc.createOffer();
		await pc.setLocalDescription(offer);
		console.log('Local description set, sending offer to', offerUrl);

		// Envoyer l'offer au serveur et attendre la answer (serveur attend SDP offer et répond SDP answer)
		let answerJson;
		try {
			answerJson = await postJson(offerUrl, { sdp: pc.localDescription.sdp, type: pc.localDescription.type });
		} catch (e) {
			console.error('Failed to send offer to server:', e);
			throw e;
		}

		// Si le serveur renvoie directement la answer SDP, la poser
		if (answerJson && answerJson.sdp) {
			try {
				const remoteDesc = { type: answerJson.type || 'answer', sdp: answerJson.sdp };
				await pc.setRemoteDescription(new RTCSessionDescription(remoteDesc));
				console.log('Remote description set from server answer');
			} catch (e) {
				console.error('Failed to set remote description:', e);
			}
		} else {
			console.warn('No SDP answer in server response');
		}

		// Retour utile pour intégration (permet d'envoyer commandes via dataChannel)
		// expose aussi sendCommand pour usage direct
		const api = { pc, dataChannel: dc, sendCommand };
		if (options.exposeGlobal) {
			window.sendCommand = sendCommand;
		}
		return api;
	}

	// Expose API minimal dans window pour intégration
	window.startWebRTC = startWebRTC;

	// ...existing code...
})();