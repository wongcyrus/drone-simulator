"""
Unit tests for FastAPI backend server functionality
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.server import app, drone_state_manager, websocket_manager, config_manager
from backend.models import DroneState, Vector3


class TestDroneStateManager:
    """Test cases for DroneStateManager class"""
    
    @pytest.fixture
    def drone_state_manager_instance(self):
        """Create a fresh DroneStateManager instance for testing"""
        from backend.server import DroneStateManager
        return DroneStateManager()
    
    @pytest.fixture
    def sample_drone_state(self):
        """Create a sample drone state for testing"""
        return DroneState(
            drone_id="test_drone",
            udp_port=8889,
            position=Vector3(100, 200, 150),
            rotation=Vector3(0, 0, 90),
            velocity=Vector3(10, 20, 5),
            is_flying=True,
            battery=85
        )
    
    def test_add_drone(self, drone_state_manager_instance, sample_drone_state):
        """Test adding a drone to the manager"""
        drone_state_manager_instance.add_drone(sample_drone_state)
        
        assert "test_drone" in drone_state_manager_instance.drones
        assert drone_state_manager_instance.drones["test_drone"] == sample_drone_state
        assert "test_drone" in drone_state_manager_instance.last_update_times
    
    def test_update_drone_state(self, drone_state_manager_instance, sample_drone_state):
        """Test updating drone state"""
        # Add drone first
        drone_state_manager_instance.add_drone(sample_drone_state)
        
        # Update state
        state_update = {
            "position": {"x": 300, "y": 400, "z": 200},
            "battery": 75,
            "is_flying": False
        }
        
        success = drone_state_manager_instance.update_drone_state("test_drone", state_update)
        assert success
        
        # Verify updates
        updated_drone = drone_state_manager_instance.get_drone_state("test_drone")
        assert updated_drone.position.x == 300
        assert updated_drone.position.y == 400
        assert updated_drone.position.z == 200
        assert updated_drone.battery == 75
        assert not updated_drone.is_flying
    
    def test_update_nonexistent_drone(self, drone_state_manager_instance):
        """Test updating a drone that doesn't exist"""
        success = drone_state_manager_instance.update_drone_state("nonexistent", {})
        assert not success
    
    def test_get_drone_state(self, drone_state_manager_instance, sample_drone_state):
        """Test getting drone state"""
        drone_state_manager_instance.add_drone(sample_drone_state)
        
        retrieved_state = drone_state_manager_instance.get_drone_state("test_drone")
        assert retrieved_state == sample_drone_state
        
        # Test nonexistent drone
        assert drone_state_manager_instance.get_drone_state("nonexistent") is None
    
    def test_get_all_drones(self, drone_state_manager_instance):
        """Test getting all drone states"""
        drone1 = DroneState("drone1", 8889)
        drone2 = DroneState("drone2", 8890)
        
        drone_state_manager_instance.add_drone(drone1)
        drone_state_manager_instance.add_drone(drone2)
        
        all_drones = drone_state_manager_instance.get_all_drones()
        assert len(all_drones) == 2
        assert "drone1" in all_drones
        assert "drone2" in all_drones
    
    def test_remove_drone(self, drone_state_manager_instance, sample_drone_state):
        """Test removing a drone"""
        drone_state_manager_instance.add_drone(sample_drone_state)
        
        success = drone_state_manager_instance.remove_drone("test_drone")
        assert success
        assert "test_drone" not in drone_state_manager_instance.drones
        assert "test_drone" not in drone_state_manager_instance.last_update_times
        
        # Test removing nonexistent drone
        success = drone_state_manager_instance.remove_drone("nonexistent")
        assert not success
    
    def test_cleanup_inactive_drones(self, drone_state_manager_instance):
        """Test cleanup of inactive drones"""
        import time
        
        drone1 = DroneState("drone1", 8889)
        drone2 = DroneState("drone2", 8890)
        
        drone_state_manager_instance.add_drone(drone1)
        drone_state_manager_instance.add_drone(drone2)
        
        # Simulate old timestamp for drone1
        drone_state_manager_instance.last_update_times["drone1"] = time.time() - 60  # 60 seconds ago
        
        inactive_drones = drone_state_manager_instance.cleanup_inactive_drones(30)  # 30 second timeout
        
        assert "drone1" in inactive_drones
        assert "drone1" not in drone_state_manager_instance.drones
        assert "drone2" in drone_state_manager_instance.drones  # Should still be active


class TestWebSocketManager:
    """Test cases for WebSocketManager class"""
    
    @pytest.fixture
    def websocket_manager_instance(self):
        """Create a fresh WebSocketManager instance for testing"""
        from backend.server import WebSocketManager
        return WebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing"""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, websocket_manager_instance, mock_websocket):
        """Test WebSocket connection"""
        await websocket_manager_instance.connect(mock_websocket)
        
        assert mock_websocket in websocket_manager_instance.active_connections
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_websocket(self, websocket_manager_instance, mock_websocket):
        """Test WebSocket disconnection"""
        # Add connection first
        websocket_manager_instance.active_connections.append(mock_websocket)
        
        websocket_manager_instance.disconnect(mock_websocket)
        
        assert mock_websocket not in websocket_manager_instance.active_connections
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, websocket_manager_instance, mock_websocket):
        """Test sending personal message"""
        await websocket_manager_instance.send_personal_message("test message", mock_websocket)
        
        mock_websocket.send_text.assert_called_once_with("test message")
    
    @pytest.mark.asyncio
    async def test_send_personal_message_error(self, websocket_manager_instance, mock_websocket):
        """Test handling error in personal message"""
        mock_websocket.send_text.side_effect = Exception("Connection error")
        websocket_manager_instance.active_connections.append(mock_websocket)
        
        await websocket_manager_instance.send_personal_message("test message", mock_websocket)
        
        # Should be disconnected after error
        assert mock_websocket not in websocket_manager_instance.active_connections
    
    @pytest.mark.asyncio
    async def test_broadcast(self, websocket_manager_instance):
        """Test broadcasting to all connections"""
        mock_ws1 = Mock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock()
        
        websocket_manager_instance.active_connections = [mock_ws1, mock_ws2]
        
        await websocket_manager_instance.broadcast("test broadcast")
        
        mock_ws1.send_text.assert_called_once_with("test broadcast")
        mock_ws2.send_text.assert_called_once_with("test broadcast")
    
    @pytest.mark.asyncio
    async def test_broadcast_with_error(self, websocket_manager_instance):
        """Test broadcasting with connection error"""
        mock_ws1 = Mock(spec=WebSocket)
        mock_ws1.send_text = AsyncMock()
        mock_ws2 = Mock(spec=WebSocket)
        mock_ws2.send_text = AsyncMock(side_effect=Exception("Connection error"))
        
        websocket_manager_instance.active_connections = [mock_ws1, mock_ws2]
        
        await websocket_manager_instance.broadcast("test broadcast")
        
        # First connection should receive message
        mock_ws1.send_text.assert_called_once_with("test broadcast")
        # Second connection should be removed due to error
        assert mock_ws2 not in websocket_manager_instance.active_connections
        assert mock_ws1 in websocket_manager_instance.active_connections
    
    def test_serialize_drone_state(self, websocket_manager_instance):
        """Test drone state serialization"""
        drone_state = DroneState(
            drone_id="test_drone",
            udp_port=8889,
            position=Vector3(100, 200, 150),
            rotation=Vector3(5, 10, 90),
            velocity=Vector3(20, 30, 5),
            acceleration=Vector3(1, 2, -980),
            is_flying=True,
            battery=85,
            temperature=35,
            flight_time=120
        )
        
        serialized = websocket_manager_instance._serialize_drone_state(drone_state)
        
        assert serialized["drone_id"] == "test_drone"
        assert serialized["udp_port"] == 8889
        assert serialized["position"]["x"] == 100
        assert serialized["position"]["y"] == 200
        assert serialized["position"]["z"] == 150
        assert serialized["rotation"]["z"] == 90
        assert serialized["velocity"]["x"] == 20
        assert serialized["acceleration"]["z"] == -980
        assert serialized["is_flying"] is True
        assert serialized["battery"] == 85
        assert serialized["temperature"] == 35
        assert serialized["flight_time"] == 120


class TestBackendAPI:
    """Test cases for FastAPI backend endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear drone state manager before each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        yield
        # Clear after each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_drones" in data
        assert "websocket_connections" in data
    
    def test_get_config(self, client):
        """Test get configuration endpoint"""
        response = client.get("/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "backend_port" in data
        assert "max_drones" in data
        assert "base_udp_port" in data
        assert "scene_bounds" in data
    
    def test_update_config(self, client):
        """Test update configuration endpoint"""
        config_update = {
            "max_drones": 15,
            "default_speed": 80
        }
        
        response = client.post("/api/config", json=config_update)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    def test_get_all_drones_empty(self, client):
        """Test getting all drones when none exist"""
        response = client.get("/api/drones")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 0
        assert data["drones"] == {}
    
    def test_update_drone_state_new_drone(self, client):
        """Test updating state for a new drone"""
        state_update = {
            "udp_port": 8889,
            "position": {"x": 100, "y": 200, "z": 150},
            "is_flying": True,
            "battery": 85
        }
        
        response = client.post("/api/drones/test_drone/state", json=state_update)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Verify drone was added
        assert "test_drone" in drone_state_manager.drones
        drone_state = drone_state_manager.get_drone_state("test_drone")
        assert drone_state.position.x == 100
        assert drone_state.is_flying is True
        assert drone_state.battery == 85
    
    def test_update_drone_state_existing_drone(self, client):
        """Test updating state for an existing drone"""
        # Add drone first
        drone_state = DroneState("test_drone", 8889)
        drone_state_manager.add_drone(drone_state)
        
        state_update = {
            "position": {"x": 300, "y": 400, "z": 200},
            "battery": 75
        }
        
        response = client.post("/api/drones/test_drone/state", json=state_update)
        assert response.status_code == 200
        
        # Verify update
        updated_drone = drone_state_manager.get_drone_state("test_drone")
        assert updated_drone.position.x == 300
        assert updated_drone.battery == 75
    
    def test_get_specific_drone_state(self, client):
        """Test getting specific drone state"""
        # Add drone first
        drone_state = DroneState(
            "test_drone", 8889,
            position=Vector3(100, 200, 150),
            battery=85
        )
        drone_state_manager.add_drone(drone_state)
        
        response = client.get("/api/drones/test_drone")
        assert response.status_code == 200
        
        data = response.json()
        assert data["drone_id"] == "test_drone"
        assert data["position"]["x"] == 100
        assert data["battery"] == 85
    
    def test_get_nonexistent_drone_state(self, client):
        """Test getting state for nonexistent drone"""
        response = client.get("/api/drones/nonexistent")
        assert response.status_code == 404
    
    def test_remove_drone(self, client):
        """Test removing a drone"""
        # Add drone first
        drone_state = DroneState("test_drone", 8889)
        drone_state_manager.add_drone(drone_state)
        
        response = client.delete("/api/drones/test_drone")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Verify drone was removed
        assert "test_drone" not in drone_state_manager.drones
    
    def test_remove_nonexistent_drone(self, client):
        """Test removing a nonexistent drone"""
        response = client.delete("/api/drones/nonexistent")
        assert response.status_code == 404
    
    def test_get_all_drones_with_data(self, client):
        """Test getting all drones when some exist"""
        # Add test drones
        drone1 = DroneState("drone1", 8889, battery=80)
        drone2 = DroneState("drone2", 8890, battery=90)
        
        drone_state_manager.add_drone(drone1)
        drone_state_manager.add_drone(drone2)
        
        response = client.get("/api/drones")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 2
        assert "drone1" in data["drones"]
        assert "drone2" in data["drones"]
        assert data["drones"]["drone1"]["battery"] == 80
        assert data["drones"]["drone2"]["battery"] == 90


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear drone state manager before each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        websocket_manager.active_connections.clear()
        yield
        # Clear after each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        websocket_manager.active_connections.clear()
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as websocket:
            # Connection should be established
            assert len(websocket_manager.active_connections) == 1
    
    def test_websocket_receives_existing_drones(self):
        """Test that new WebSocket connections receive existing drone states"""
        # Add a drone before connecting
        drone_state = DroneState("test_drone", 8889, battery=85)
        drone_state_manager.add_drone(drone_state)
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as websocket:
            # Should receive drone_added message for existing drone
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == "drone_added"
            assert message["drone_id"] == "test_drone"
            assert message["initial_state"]["battery"] == 85


if __name__ == "__main__":
    pytest.main([__file__])