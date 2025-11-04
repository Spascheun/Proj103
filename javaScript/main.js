import { webRTCClient } from "./WebRTCClient.js";
import { WebSocketClient } from "./WebSocketClient.js";


async function createClient(type = 'webrtc') {
    if (type === 'webrtc') {
        try {
            const rtcClient = new webRTCClient({offerUrl: '/rtcOffer_command'});
            await rtcClient.ready;
            console.log('WebRTC client initialized');
            await rtcClient.dcReady;
            console.log('WebRTC DataChannel is open');
            return rtcClient;
        } 
        catch (e) {
            console.warn('WebRTC initialization failed, falling back to WebSocket', e);
            const wsClient = new WebSocketClient('ws://' + window.location.host + '/ws');
            console.log('WebSocket client created as fallback');
            await wsClient.ready;
            console.log('WebSocket connection open');
            return wsClient;
        }
    } 
    else if (type === 'websocket') {
        const wsClient = new WebSocketClient('ws://' + window.location.host + '/ws');
        console.log('WebSocket client created');
        await wsClient.ready;
        console.log('WebSocket connection open');
        return wsClient;
    }
}

export { createClient };

