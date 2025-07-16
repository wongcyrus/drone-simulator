/**
 * Main application entry point for RoboMaster TT 3D Simulator
 */

class SimulatorApp {
    constructor() {
        this.scene3d = null;
        this.droneRenderer = null;
        this.websocketClient = null;
        this.uiController = null;
        this.drones = new Map();
        
        this.init();
    }
    
    async init() {
        try {
            // Initialize 3D scene
            this.scene3d = new Scene3D('canvas-container');
            
            // Initialize drone renderer
            this.droneRenderer = new DroneRenderer(this.scene3d);
            
            // Initialize UI controller
            this.uiController = new UIController();
            
            // Initialize WebSocket connection
            this.websocketClient = new WebSocketClient('ws://localhost:8000/ws');
            this.setupWebSocketHandlers();
            
            // Start render loop
            this.animate();
            
            console.log('RoboMaster TT 3D Simulator initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize simulator:', error);
        }
    }
    
    setupWebSocketHandlers() {
        this.websocketClient.on('connected', () => {
            console.log('Connected to backend server');
            this.uiController.setConnectionStatus(true);
        });
        
        this.websocketClient.on('disconnected', () => {
            console.log('Disconnected from backend server');
            this.uiController.setConnectionStatus(false);
        });
        
        this.websocketClient.on('drone_state_update', (data) => {
            this.handleDroneStateUpdate(data);
        });
        
        this.websocketClient.on('drone_added', (data) => {
            this.handleDroneAdded(data);
        });
        
        this.websocketClient.on('drone_removed', (data) => {
            this.handleDroneRemoved(data);
        });
    }
    
    handleDroneStateUpdate(data) {
        const { drone_id, state } = data;
        
        if (this.drones.has(drone_id)) {
            // Update existing drone
            this.drones.set(drone_id, state);
            this.droneRenderer.updateDrone(drone_id, state);
            this.uiController.updateDroneInfo(drone_id, state);
        }
    }
    
    handleDroneAdded(data) {
        const { drone_id, initial_state } = data;
        
        // Add drone to local storage
        this.drones.set(drone_id, initial_state);
        
        // Create 3D representation
        this.droneRenderer.addDrone(drone_id, initial_state);
        
        // Update UI
        this.uiController.addDrone(drone_id, initial_state);
        
        console.log(`Drone ${drone_id} added to simulation`);
    }
    
    handleDroneRemoved(data) {
        const { drone_id } = data;
        
        if (this.drones.has(drone_id)) {
            // Remove from local storage
            this.drones.delete(drone_id);
            
            // Remove 3D representation
            this.droneRenderer.removeDrone(drone_id);
            
            // Update UI
            this.uiController.removeDrone(drone_id);
            
            console.log(`Drone ${drone_id} removed from simulation`);
        }
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.scene3d) {
            this.scene3d.render();
        }
        
        if (this.droneRenderer) {
            this.droneRenderer.update();
        }
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.simulatorApp = new SimulatorApp();
});