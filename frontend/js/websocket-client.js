/**
 * WebSocketClient - Handles WebSocket communication with backend server
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        
        // Event handlers
        this.eventHandlers = {
            connected: [],
            disconnected: [],
            error: [],
            message: [],
            drone_state_update: [],
            drone_added: [],
            drone_removed: []
        };
        
        this.connect();
    }
    
    connect() {
        try {
            console.log(`Connecting to WebSocket: ${this.url}`);
            this.websocket = new WebSocket(this.url);
            
            this.websocket.onopen = (event) => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000; // Reset delay
                this.emit('connected', event);
            };
            
            this.websocket.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.emit('disconnected', event);
                
                // Attempt to reconnect if not a clean close
                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };
            
            this.websocket.onerror = (event) => {
                console.error('WebSocket error:', event);
                this.emit('error', event);
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                    console.error('Raw message:', event.data);
                }
            };
            
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }
    
    handleMessage(data) {
        console.log('WebSocket message received:', data);
        
        // Emit general message event
        this.emit('message', data);
        
        // Emit specific event based on message type
        if (data.type && this.eventHandlers[data.type]) {
            this.emit(data.type, data);
        }
    }
    
    send(data) {
        if (!this.isConnected || !this.websocket) {
            console.warn('WebSocket not connected, cannot send message');
            return false;
        }
        
        try {
            const message = typeof data === 'string' ? data : JSON.stringify(data);
            this.websocket.send(message);
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            return false;
        }
    }
    
    // Event system
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }
    
    off(event, handler) {
        if (!this.eventHandlers[event]) return;
        
        const index = this.eventHandlers[event].indexOf(handler);
        if (index > -1) {
            this.eventHandlers[event].splice(index, 1);
        }
    }
    
    emit(event, data) {
        if (!this.eventHandlers[event]) return;
        
        this.eventHandlers[event].forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in event handler for '${event}':`, error);
            }
        });
    }
    
    // Connection management
    disconnect() {
        if (this.websocket) {
            this.websocket.close(1000, 'Client disconnect');
        }
    }
    
    reconnect() {
        this.disconnect();
        setTimeout(() => this.connect(), 100);
    }
    
    getConnectionState() {
        if (!this.websocket) return 'CLOSED';
        
        switch (this.websocket.readyState) {
            case WebSocket.CONNECTING:
                return 'CONNECTING';
            case WebSocket.OPEN:
                return 'OPEN';
            case WebSocket.CLOSING:
                return 'CLOSING';
            case WebSocket.CLOSED:
                return 'CLOSED';
            default:
                return 'UNKNOWN';
        }
    }
    
    isReady() {
        return this.isConnected && this.websocket && this.websocket.readyState === WebSocket.OPEN;
    }
    
    // Utility methods for common message types
    sendPing() {
        return this.send({ type: 'ping', timestamp: Date.now() });
    }
    
    requestDroneList() {
        return this.send({ type: 'request_drone_list' });
    }
    
    requestDroneState(droneId) {
        return this.send({ type: 'request_drone_state', drone_id: droneId });
    }
    
    // Cleanup
    dispose() {
        // Remove all event handlers
        Object.keys(this.eventHandlers).forEach(event => {
            this.eventHandlers[event] = [];
        });
        
        // Close connection
        this.disconnect();
        
        console.log('WebSocketClient disposed');
    }
}