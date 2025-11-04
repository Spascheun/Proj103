const USING_STUN = true;

const DEFAULT_PUBLIC_STUN = [
	{ urls: "stun:stun.l.google.com:19302" },
	{ urls: "stun:stun1.l.google.com:19302" },
	{ urls: "stun:stun2.l.google.com:19302" }
];

// --- classe webRTCClient -------------------------------------------------------
class webRTCClient {
	constructor(options = {}) {
		this.options = options;
		this.pc = null;
		this.dc = null;
		this._sendBuffer = [];
		// ready est une Promise résolue quand la négociation est terminée
		this.ready = this._init();
	}

	// Envoie JSON au serveur et retourne la réponse JSON
	async postJson(url, body) {
		const res = await fetch(url, {
			method: 'POST',
			body: JSON.stringify(body),
			headers: { 'Content-Type': 'application/json' }
		});
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		return await res.json();
	}

	// méthode publique pour envoyer des commandes (bufferise si nécessaire)
	sendCommand(x, y) {
		let msg;
		try { msg = JSON.stringify({ x, y }); } catch (e) { console.warn('Failed to serialize command', e); return false; }
		if (this.dc && this.dc.readyState === 'open') {
			try { this.dc.send(msg); return true; } catch (e) { console.warn('Send failed', e); return false; }
		} else { 
			console.warn('DataChannel not open');
			return false;
		}
	}

	// initialisation asynchrone : récupère iceServers -> createPeer -> createOffer -> POST offer -> setRemoteDescription(answer)
	async _init() {
		const offerUrl = this.options.offerUrl || '/offer_command';
		try {
			const iceServers = DEFAULT_PUBLIC_STUN;
			const pcConfig = { iceServers };
			this.pc = USING_STUN ? new RTCPeerConnection(pcConfig) : new RTCPeerConnection();

			// create data channel AFTER pc created
			this.dc = this.pc.createDataChannel('commands');

			const offer = await this.pc.createOffer();
			await this.pc.setLocalDescription(offer);
			console.log('Local description set, sending offer to', offerUrl);

			const answerJson = await this.postJson(offerUrl, { sdp: this.pc.localDescription.sdp, type: this.pc.localDescription.type });

			if (answerJson && answerJson.sdp) {
				const remoteDesc = { type: answerJson.type || 'answer', sdp: answerJson.sdp };
				await this.pc.setRemoteDescription(new RTCSessionDescription(remoteDesc));
				console.log('Remote description set from server answer');
			} else {
				console.warn('No SDP answer in server response');
				throw new Error('Invalid answer from server');
			}
			return { pc: this.pc, dataChannel: this.dc, sendCommand: this.sendCommand.bind(this) };
		} catch (e) {
			console.error('Negotiation failed:', e);
			throw e;
		}
	}

	// optionnel : wrapper pour fermer proprement
	async close() {
		try { if (this.dc) this.dc.close(); } catch (_) {}
		try { if (this.pc) await this.pc.close(); } catch (_) {}
	}
}
// --- fin de la classe webRTCClient ---------------------------------------


// Exporte la classe pour usage en module
export { webRTCClient };