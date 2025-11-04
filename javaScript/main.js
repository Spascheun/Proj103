import { webRTCClient } from "./WebRTCClient";
import { WebSocketClient } from "./WebSocketClient";


async function createClient() {
    try {
        const rtcClient = new webRTCClient({offerUrl: '/offer_command'});
        await rtcClient.ready;
        console.log('WebRTC client initialized');
        
        return rtcClient;
    } catch (e) {
        console.warn('WebRTC initialization failed, falling back to WebSocket', e);
        const wsClient = new WebSocketClient();
        console.log('WebSocket client created as fallback');
        return wsClient;
    }
}

export { createClient };

