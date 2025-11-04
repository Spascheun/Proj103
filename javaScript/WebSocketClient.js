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
		this.type = 'websocket';
		this.url = url;
		this.ws = null;
		this.ready = null;
		this.state = 'closed'; // 'connecting','open','closed'
		this.onOpen = opts.onOpen || (()=>{});
		this.onError = opts.onError || ((e)=>{ console.warn('WS error', e); });
		this.connect();
	}

	connect() {
		if (this.state === 'connecting' || this.state === 'open') return;
		this.state = 'connecting';
		try {
			this.ws = new WebSocket(this.url);
		} catch (e) {
			this._handleError(e);
			return;
		}

		this.ready = new Promise((resolve, reject) => {
			if (this.ws.readyState === WebSocket.OPEN) {
				this.state = 'open';
				resolve();
			} else {
				this.ws.addEventListener('open', (ev) => {
					this.state = 'open';
					resolve();
				});
			}
		});

		// nouveau: gestion de l'ouverture -> état, callback et vidange du buffer
		this.ws.onopen = (ev) => {
			this.state = 'open';
		};

		this.ws.onerror = (ev) => {
			this._handleError(ev);
		};

		this.ws.onclose = (ev) => {
			this.state = 'closed';
			this.onClose(ev);
		};
	}

	sendCommand(x, y) {
		return this.send({ x, y });
	}

	send(obj) {
		let msg;
		try {
			msg = JSON.stringify(obj);
		} catch (e) {
			console.warn('WS send: failed to serialize', e);
			return false;
		}
		if (this.state === 'open' && this.ws && this.ws.readyState === WebSocket.OPEN) {
			try {
				this.ws.send(msg);
				return true;
			} catch (e) {
				console.warn('WS send failed', e);
				return false;
			}
		
		} else {
			console.warn('WS not open, cannot send');
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

export { WebSocketClient };
