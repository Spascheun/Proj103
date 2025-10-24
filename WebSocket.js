/* Client WebSocket minimal réutilisable (navigateur).
   Usage :
     const client = new WebSocketClient('ws://host:port/path', { protocols: ['json'], reconnect: true });
     client.onMessage = (msg) => { ... };
     client.connect();
     client.send({type:'cmd', val: 42});
     client.close();
*/
class WebSocketClient {
	constructor(url, opts = {}) {
		this.url = url;
		this.protocols = opts.protocols;
		this.ws = null;
		this.state = 'closed'; // 'connecting','open','closed'
		// callbacks exposés
		this.onOpen = opts.onOpen || (()=>{});
		this.onMessage = opts.onMessage || ((m)=>{ console.log('WS msg', m); });
		this.onClose = opts.onClose || (()=>{});
		this.onError = opts.onError || ((e)=>{ console.warn('WS error', e); });

		// buffer pour envois avant ouverture
		this.sendBuffer = [];
	}

	connect() {
		if (this.state === 'connecting' || this.state === 'open') return;
		this.state = 'connecting';
		try {
			this.ws = this.protocols ? new WebSocket(this.url, this.protocols) : new WebSocket(this.url);
		} catch (e) {
			this._handleError(e);
			return;
		}

		// nouveau: gestion de l'ouverture -> état, callback et vidange du buffer
		this.ws.onopen = (ev) => {
			this.state = 'open';
			this.onOpen(ev);
			// flush buffer
			while (this.sendBuffer.length > 0 && this.state === 'open' && this.ws && this.ws.readyState === WebSocket.OPEN) {
				const m = this.sendBuffer.shift();
				try { this.ws.send(m); } catch (e) {
					console.warn('WS flush failed, requeue', e);
					this.sendBuffer.unshift(m);
					break;
				}
			}
		};

		// nouveau: parser JSON si possible puis appeler onMessage
		this.ws.onmessage = (ev) => {
			let data = ev.data;
			try { data = JSON.parse(ev.data); } catch (e) { /* keep raw */ }
			this.onMessage(data);
		};

		this.ws.onerror = (ev) => {
			this._handleError(ev);
		};

		this.ws.onclose = (ev) => {
			this.state = 'closed';
			this.onClose(ev);
		};
	}

	send(obj) {
		let msg;
		try {
			msg = (typeof obj === 'string') ? obj : JSON.stringify(obj);
		} catch (e) {
			console.warn('WS send: failed to serialize', e);
			return false;
		}
		if (this.state === 'open' && this.ws && this.ws.readyState === WebSocket.OPEN) {
			try {
				this.ws.send(msg);
				return true;
			} catch (e) {
				console.warn('WS send failed, buffering', e);
				this.sendBuffer.push(msg);
				return false;
			}
		} else {
			// bufferise si pas encore ouvert
			this.sendBuffer.push(msg);
			return false;
		}
	}

	close(code = 1000, reason) {
		if (this.ws) {
			try { this.ws.close(code, reason); } catch (e) { /* ignore */ }
		}
		this.state = 'closed';
	}

	_handleError(e) {
		try { this.onError(e); } catch (ex) { console.warn('onError handler threw', ex); }
	}
}

// Expose global helper
window.WebSocketClient = WebSocketClient;
