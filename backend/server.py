"""
FastAPI backend server for RoboMaster TT 3D Simulator
Manages drone states and provides API endpoints for mock drones and web clients
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uvicorn
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import DroneState, SimulationConfig, Vector3
from backend.config import ConfigManager


class DroneStateManager:
    """Manages all drone states and coordinates updates"""
    
    def __init__(self):
        self.drones: Dict[str, DroneState] = {}
        self.last_update_times: Dict[str, float] = {}
        self.logger = logging.getLogger("DroneStateManager")
    
    def add_drone(self, drone_state: DroneState) -> None:
        """Add a new drone to the simulation"""
        self.drones[drone_state.drone_id] = drone_state
        self.last_update_times[drone_state.drone_id] = datetime.now().timestamp()
        self.logger.info(f"Added drone {drone_state.drone_id} on port {drone_state.udp_port}")
    
    def update_drone_state(self, drone_id: str, state_update: Dict[str, Any]) -> bool:
        """Update drone state with new data"""
        if drone_id not in self.drones:
            return False
        
        drone_state = self.drones[drone_id]
        
        # Update position
        if 'position' in state_update:
            pos = state_update['position']
            drone_state.position = Vector3(pos.get('x', 0), pos.get('y', 0), pos.get('z', 0))
        
        # Update rotation
        if 'rotation' in state_update:
            rot = state_update['rotation']
            drone_state.rotation = Vector3(rot.get('x', 0), rot.get('y', 0), rot.get('z', 0))
        
        # Update velocity
        if 'velocity' in state_update:
            vel = state_update['velocity']
            drone_state.velocity = Vector3(vel.get('x', 0), vel.get('y', 0), vel.get('z', 0))
        
        # Update other fields
        for field in ['is_flying', 'is_connected', 'battery', 'temperature', 'flight_time', 
                     'barometer', 'mission_pad_id', 'mission_pad_x', 'mission_pad_y', 'mission_pad_z',
                     'speed', 'rc_values']:
            if field in state_update:
                setattr(drone_state, field, state_update[field])
        
        # Update acceleration
        if 'acceleration' in state_update:
            acc = state_update['acceleration']
            drone_state.acceleration = Vector3(acc.get('x', 0), acc.get('y', 0), acc.get('z', 0))
        
        # Update timestamps
        drone_state.last_update_time = datetime.now().timestamp()
        self.last_update_times[drone_id] = drone_state.last_update_time
        
        return True
    
    def get_drone_state(self, drone_id: str) -> Optional[DroneState]:
        """Get drone state by ID"""
        return self.drones.get(drone_id)
    
    def get_all_drones(self) -> Dict[str, DroneState]:
        """Get all drone states"""
        return self.drones.copy()
    
    def remove_drone(self, drone_id: str) -> bool:
        """Remove drone from simulation"""
        if drone_id in self.drones:
            del self.drones[drone_id]
            if drone_id in self.last_update_times:
                del self.last_update_times[drone_id]
            self.logger.info(f"Removed drone {drone_id}")
            return True
        return False
    
    def cleanup_inactive_drones(self, timeout_seconds: int = 30) -> List[str]:
        """Remove drones that haven't updated in timeout_seconds"""
        current_time = datetime.now().timestamp()
        inactive_drones = []
        
        for drone_id, last_update in self.last_update_times.items():
            if current_time - last_update > timeout_seconds:
                inactive_drones.append(drone_id)
        
        for drone_id in inactive_drones:
            self.remove_drone(drone_id)
        
        return inactive_drones


class WebSocketManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger("WebSocketManager")
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected WebSockets"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_drone_state_update(self, drone_id: str, drone_state: DroneState):
        """Broadcast drone state update to all clients"""
        message = {
            "type": "drone_state_update",
            "drone_id": drone_id,
            "state": self._serialize_drone_state(drone_state)
        }
        await self.broadcast(json.dumps(message))
    
    async def broadcast_drone_added(self, drone_id: str, drone_state: DroneState):
        """Broadcast drone added event to all clients"""
        message = {
            "type": "drone_added",
            "drone_id": drone_id,
            "initial_state": self._serialize_drone_state(drone_state)
        }
        await self.broadcast(json.dumps(message))
    
    async def broadcast_drone_removed(self, drone_id: str):
        """Broadcast drone removed event to all clients"""
        message = {
            "type": "drone_removed",
            "drone_id": drone_id
        }
        await self.broadcast(json.dumps(message))
    
    def _serialize_drone_state(self, drone_state: DroneState) -> Dict[str, Any]:
        """Serialize drone state for JSON transmission"""
        return {
            "drone_id": drone_state.drone_id,
            "udp_port": drone_state.udp_port,
            "position": {
                "x": drone_state.position.x,
                "y": drone_state.position.y,
                "z": drone_state.position.z
            },
            "rotation": {
                "x": drone_state.rotation.x,
                "y": drone_state.rotation.y,
                "z": drone_state.rotation.z
            },
            "velocity": {
                "x": drone_state.velocity.x,
                "y": drone_state.velocity.y,
                "z": drone_state.velocity.z
            },
            "acceleration": {
                "x": drone_state.acceleration.x,
                "y": drone_state.acceleration.y,
                "z": drone_state.acceleration.z
            },
            "is_flying": drone_state.is_flying,
            "is_connected": drone_state.is_connected,
            "flight_time": drone_state.flight_time,
            "battery": drone_state.battery,
            "temperature": drone_state.temperature,
            "barometer": drone_state.barometer,
            "mission_pad_id": drone_state.mission_pad_id,
            "mission_pad_x": drone_state.mission_pad_x,
            "mission_pad_y": drone_state.mission_pad_y,
            "mission_pad_z": drone_state.mission_pad_z,
            "speed": drone_state.speed,
            "rc_values": drone_state.rc_values,
            "last_command_time": drone_state.last_command_time,
            "last_update_time": drone_state.last_update_time
        }


# Global instances
config_manager = ConfigManager()
drone_state_manager = DroneStateManager()
websocket_manager = WebSocketManager()

# FastAPI app
app = FastAPI(
    title="RoboMaster TT 3D Simulator Backend",
    description="Backend server for managing drone states and WebSocket communication",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
if os.path.exists("frontend"):
    if os.path.exists("frontend/js"):
        app.mount("/js", StaticFiles(directory="frontend/js"), name="js")
    if os.path.exists("frontend/css"):
        app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
    if os.path.exists("frontend/assets"):
        app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BackendServer")


@app.on_event("startup")
async def startup_event():
    """Initialize server on startup"""
    logger.info("Starting RoboMaster TT 3D Simulator Backend")
    
    # Start cleanup task for inactive drones
    asyncio.create_task(cleanup_inactive_drones_task())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Shutting down RoboMaster TT 3D Simulator Backend")


async def cleanup_inactive_drones_task():
    """Background task to cleanup inactive drones"""
    while True:
        try:
            inactive_drones = drone_state_manager.cleanup_inactive_drones(30)
            for drone_id in inactive_drones:
                await websocket_manager.broadcast_drone_removed(drone_id)
                logger.info(f"Cleaned up inactive drone: {drone_id}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(10)


# API Routes

@app.get("/")
async def root():
    """Serve the main frontend page"""
    if os.path.exists("frontend/index.html"):
        with open("frontend/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    return {"message": "RoboMaster TT 3D Simulator Backend", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_drones": len(drone_state_manager.drones),
        "websocket_connections": len(websocket_manager.active_connections)
    }


@app.post("/api/drones/{drone_id}/state")
async def update_drone_state(drone_id: str, state_update: Dict[str, Any]):
    """Update drone state from mock drone client"""
    try:
        # Check if drone exists, if not create it
        if drone_id not in drone_state_manager.drones:
            # Create new drone state
            drone_state = DroneState(
                drone_id=drone_id,
                udp_port=state_update.get('udp_port', 8889)
            )
            drone_state_manager.add_drone(drone_state)
            await websocket_manager.broadcast_drone_added(drone_id, drone_state)
        
        # Update drone state
        success = drone_state_manager.update_drone_state(drone_id, state_update)
        if not success:
            raise HTTPException(status_code=404, detail="Drone not found")
        
        # Broadcast update to WebSocket clients
        updated_state = drone_state_manager.get_drone_state(drone_id)
        await websocket_manager.broadcast_drone_state_update(drone_id, updated_state)
        
        return {"status": "success", "message": f"Updated drone {drone_id}"}
        
    except Exception as e:
        logger.error(f"Error updating drone state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/drones")
async def get_all_drones():
    """Get all drone states"""
    drones = drone_state_manager.get_all_drones()
    serialized_drones = {}
    
    for drone_id, drone_state in drones.items():
        serialized_drones[drone_id] = websocket_manager._serialize_drone_state(drone_state)
    
    return {
        "drones": serialized_drones,
        "count": len(drones)
    }


@app.get("/api/drones/{drone_id}")
async def get_drone_state(drone_id: str):
    """Get specific drone state"""
    drone_state = drone_state_manager.get_drone_state(drone_id)
    if not drone_state:
        raise HTTPException(status_code=404, detail="Drone not found")
    
    return websocket_manager._serialize_drone_state(drone_state)


@app.delete("/api/drones/{drone_id}")
async def remove_drone(drone_id: str):
    """Remove drone from simulation"""
    success = drone_state_manager.remove_drone(drone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Drone not found")
    
    # Broadcast removal to WebSocket clients
    await websocket_manager.broadcast_drone_removed(drone_id)
    
    return {"status": "success", "message": f"Removed drone {drone_id}"}


@app.get("/api/config")
async def get_config():
    """Get current simulation configuration"""
    config = config_manager.get_config()
    return {
        "backend_port": config.backend_port,
        "websocket_port": config.websocket_port,
        "max_drones": config.max_drones,
        "base_udp_port": config.base_udp_port,
        "default_speed": config.default_speed,
        "gravity": config.gravity,
        "air_resistance": config.air_resistance,
        "max_acceleration": config.max_acceleration,
        "update_rate": config.update_rate,
        "battery_drain_rate": config.battery_drain_rate,
        "scene_bounds": list(config.scene_bounds)
    }


@app.post("/api/config")
async def update_config(config_update: Dict[str, Any]):
    """Update simulation configuration"""
    try:
        config_manager.update_config(config_update)
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket_manager.connect(websocket)
    
    try:
        # Send current drone states to new client
        drones = drone_state_manager.get_all_drones()
        for drone_id, drone_state in drones.items():
            await websocket_manager.send_personal_message(
                json.dumps({
                    "type": "drone_added",
                    "drone_id": drone_id,
                    "initial_state": websocket_manager._serialize_drone_state(drone_state)
                }),
                websocket
            )
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            logger.info(f"Received WebSocket message: {data}")
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


def main():
    """Main function to run the server"""
    config = config_manager.get_config()
    
    # Configure uvicorn logging to be less verbose
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"
    
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=config.backend_port,
        reload=False,
        log_level="warning",  # Reduce general log level
        log_config=uvicorn_log_config
    )


if __name__ == "__main__":
    main()