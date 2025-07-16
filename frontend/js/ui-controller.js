/**
 * UIController - Manages the user interface for the RoboMaster TT 3D Simulator
 */

class UIController {
    constructor() {
        this.elements = {
            connectionStatus: document.getElementById('connection-status'),
            droneList: document.getElementById('drone-list'),
            uiPanel: document.getElementById('ui-panel')
        };
        
        this.drones = new Map();
        this.isConnected = false;
        
        this.init();
    }
    
    init() {
        this.updateConnectionStatus(false);
        this.updateDroneList();
        console.log('UIController initialized');
    }
    
    setConnectionStatus(connected) {
        this.isConnected = connected;
        this.updateConnectionStatus(connected);
    }
    
    updateConnectionStatus(connected) {
        if (!this.elements.connectionStatus) return;
        
        if (connected) {
            this.elements.connectionStatus.textContent = 'Connected';
            this.elements.connectionStatus.className = 'connected';
        } else {
            this.elements.connectionStatus.textContent = 'Disconnected';
            this.elements.connectionStatus.className = 'disconnected';
        }
    }
    
    addDrone(droneId, droneState) {
        this.drones.set(droneId, droneState);
        this.updateDroneList();
        console.log(`Added drone ${droneId} to UI`);
    }
    
    updateDroneInfo(droneId, droneState) {
        if (this.drones.has(droneId)) {
            this.drones.set(droneId, droneState);
            this.updateDroneList();
        }
    }
    
    removeDrone(droneId) {
        if (this.drones.has(droneId)) {
            this.drones.delete(droneId);
            this.updateDroneList();
            console.log(`Removed drone ${droneId} from UI`);
        }
    }
    
    updateDroneList() {
        if (!this.elements.droneList) return;
        
        if (this.drones.size === 0) {
            this.elements.droneList.innerHTML = '<p>No drones connected</p>';
            return;
        }
        
        let html = '';
        
        this.drones.forEach((droneState, droneId) => {
            html += this.createDroneInfoHTML(droneId, droneState);
        });
        
        this.elements.droneList.innerHTML = html;
    }
    
    createDroneInfoHTML(droneId, droneState) {
        const statusClass = droneState.is_connected ? 'connected' : 'disconnected';
        const flyingStatus = droneState.is_flying ? 'Flying' : 'Landed';
        const batteryClass = this.getBatteryClass(droneState.battery);
        
        return `
            <div class="drone-info" data-drone-id="${droneId}">
                <div class="drone-title">${droneId} (Port: ${droneState.udp_port})</div>
                <div class="drone-status ${statusClass}">${flyingStatus}</div>
                
                <div class="telemetry-section">
                    <div class="telemetry-row">
                        <span>Battery:</span>
                        <span class="battery-level ${batteryClass}">${droneState.battery}%</span>
                    </div>
                    <div class="telemetry-row">
                        <span>Position:</span>
                        <span>X: ${droneState.position.x.toFixed(0)}cm, Y: ${droneState.position.y.toFixed(0)}cm, Z: ${droneState.position.z.toFixed(0)}cm</span>
                    </div>
                    <div class="telemetry-row">
                        <span>Rotation:</span>
                        <span>Yaw: ${droneState.rotation.z.toFixed(0)}°</span>
                    </div>
                    <div class="telemetry-row">
                        <span>Velocity:</span>
                        <span>${this.getVelocityMagnitude(droneState.velocity).toFixed(1)} cm/s</span>
                    </div>
                    <div class="telemetry-row">
                        <span>Temperature:</span>
                        <span>${droneState.temperature}°C</span>
                    </div>
                    <div class="telemetry-row">
                        <span>Flight Time:</span>
                        <span>${this.formatFlightTime(droneState.flight_time)}</span>
                    </div>
                    ${this.createMissionPadInfo(droneState)}
                </div>
            </div>
        `;
    }
    
    createMissionPadInfo(droneState) {
        if (droneState.mission_pad_id === -1) {
            return `
                <div class="telemetry-row">
                    <span>Mission Pad:</span>
                    <span>Not detected</span>
                </div>
            `;
        }
        
        return `
            <div class="telemetry-row">
                <span>Mission Pad:</span>
                <span>ID: ${droneState.mission_pad_id}</span>
            </div>
            <div class="telemetry-row">
                <span>Pad Position:</span>
                <span>X: ${droneState.mission_pad_x}cm, Y: ${droneState.mission_pad_y}cm</span>
            </div>
        `;
    }
    
    getBatteryClass(batteryLevel) {
        if (batteryLevel > 50) return 'battery-good';
        if (batteryLevel > 20) return 'battery-medium';
        return 'battery-low';
    }
    
    getVelocityMagnitude(velocity) {
        return Math.sqrt(velocity.x * velocity.x + velocity.y * velocity.y + velocity.z * velocity.z);
    }
    
    formatFlightTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    // Statistics and summary methods
    getConnectedDroneCount() {
        let count = 0;
        this.drones.forEach(droneState => {
            if (droneState.is_connected) count++;
        });
        return count;
    }
    
    getFlyingDroneCount() {
        let count = 0;
        this.drones.forEach(droneState => {
            if (droneState.is_flying) count++;
        });
        return count;
    }
    
    getAverageBatteryLevel() {
        if (this.drones.size === 0) return 0;
        
        let totalBattery = 0;
        this.drones.forEach(droneState => {
            totalBattery += droneState.battery;
        });
        
        return Math.round(totalBattery / this.drones.size);
    }
    
    // UI interaction methods
    highlightDrone(droneId) {
        const droneElement = document.querySelector(`[data-drone-id="${droneId}"]`);
        if (droneElement) {
            droneElement.classList.add('highlighted');
            setTimeout(() => {
                droneElement.classList.remove('highlighted');
            }, 2000);
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to UI
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
    
    // Error handling
    showError(message) {
        this.showNotification(message, 'error');
        console.error('UI Error:', message);
    }
    
    showWarning(message) {
        this.showNotification(message, 'warning');
        console.warn('UI Warning:', message);
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
        console.log('UI Success:', message);
    }
    
    // Cleanup
    dispose() {
        this.drones.clear();
        
        // Clear UI elements
        if (this.elements.droneList) {
            this.elements.droneList.innerHTML = '<p>No drones connected</p>';
        }
        
        console.log('UIController disposed');
    }
}