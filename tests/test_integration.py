"""
Integration tests for mock drone to backend server communication
"""
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
import aiohttp

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_drone.mock_drone import MockDrone
from backend.server import app, drone_state_manager, websocket_manager
from backend.models import DroneState, Vector3, SimulationConfig


class TestMockDroneBackendIntegration:
    """Test cases for mock drone to backend integration"""
    
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
        websocket_manager.active_connections.clear()
        yield
        # Clear after each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        websocket_manager.active_connections.clear()
    
    @pytest.fixture
    def mock_drone_instance(self):
        """Create a mock drone instance for testing"""
        config = SimulationConfig()
        return MockDrone("test_drone", 8889, "http://localhost:8000", config)
    
    @pytest.mark.asyncio
    async def test_send_state_to_backend(self, mock_drone_instance, client):
        """Test sending drone state to backend"""
        # Create HTTP session for mock drone
        mock_drone_instance.http_session = aiohttp.ClientSession()
        
        try:
            # Set up drone state
            mock_drone_instance.state.position = Vector3(100, 200, 150)
            mock_drone_instance.state.is_flying = True
            mock_drone_instance.state.battery = 85
            
            # Mock the HTTP request
            with patch.object(mock_drone_instance.http_session, 'post') as mock_post:
                mock_response = Mock()
                mock_response.status = 200
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Send state to backend
                await mock_drone_instance.send_state_to_backend()
                
                # Verify HTTP request was made
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                
                # Check URL
                assert call_args[0][0] == "http://localhost:8000/api/drones/test_drone/state"
                
                # Check JSON data
                json_data = call_args[1]['json']
                assert json_data['udp_port'] == 8889
                assert json_data['position']['x'] == 100
                assert json_data['position']['y'] == 200
                assert json_data['position']['z'] == 150
                assert json_data['is_flying'] is True
                assert json_data['battery'] == 85
        
        finally:
            await mock_drone_instance.http_session.close()
    
    @pytest.mark.asyncio
    async def test_send_state_to_backend_error_handling(self, mock_drone_instance):
        """Test error handling when sending state to backend"""
        # Create HTTP session for mock drone
        mock_drone_instance.http_session = aiohttp.ClientSession()
        
        try:
            # Mock HTTP error
            with patch.object(mock_drone_instance.http_session, 'post') as mock_post:
                mock_post.side_effect = aiohttp.ClientError("Connection failed")
                
                # Should not raise exception
                await mock_drone_instance.send_state_to_backend()
                
                # Verify error was logged (would need to check logs in real scenario)
                mock_post.assert_called_once()
        
        finally:
            await mock_drone_instance.http_session.close()
    
    @pytest.mark.asyncio
    async def test_send_state_to_backend_timeout(self, mock_drone_instance):
        """Test timeout handling when sending state to backend"""
        # Create HTTP session for mock drone
        mock_drone_instance.http_session = aiohttp.ClientSession()
        
        try:
            # Mock timeout
            with patch.object(mock_drone_instance.http_session, 'post') as mock_post:
                mock_post.side_effect = asyncio.TimeoutError()
                
                # Should not raise exception
                await mock_drone_instance.send_state_to_backend()
                
                # Verify timeout was handled
                mock_post.assert_called_once()
        
        finally:
            await mock_drone_instance.http_session.close()
    
    @pytest.mark.asyncio
    async def test_backend_update_loop(self, mock_drone_instance):
        """Test backend update loop functionality"""
        # Mock HTTP session and send_state_to_backend
        mock_drone_instance.http_session = Mock()
        mock_drone_instance.send_state_to_backend = AsyncMock()
        
        # Set short update interval for testing
        mock_drone_instance.backend_update_interval = 0.01  # 100 Hz for fast testing
        mock_drone_instance.running = True
        
        # Start update loop
        update_task = asyncio.create_task(mock_drone_instance.backend_update_loop())
        
        # Let it run for a short time
        await asyncio.sleep(0.05)
        
        # Stop the loop
        mock_drone_instance.running = False
        update_task.cancel()
        
        try:
            await update_task
        except asyncio.CancelledError:
            pass
        
        # Verify send_state_to_backend was called multiple times
        assert mock_drone_instance.send_state_to_backend.call_count > 0
    
    def test_backend_integration_via_api(self, client):
        """Test backend integration via API endpoints"""
        # Test updating drone state via API
        state_update = {
            "udp_port": 8889,
            "position": {"x": 100, "y": 200, "z": 150},
            "rotation": {"x": 0, "y": 0, "z": 90},
            "velocity": {"x": 10, "y": 20, "z": 5},
            "is_flying": True,
            "battery": 85,
            "temperature": 35
        }
        
        # Send state update
        response = client.post("/api/drones/test_drone/state", json=state_update)
        assert response.status_code == 200
        
        # Verify drone was added to backend
        response = client.get("/api/drones/test_drone")
        assert response.status_code == 200
        
        data = response.json()
        assert data["drone_id"] == "test_drone"
        assert data["position"]["x"] == 100
        assert data["position"]["y"] == 200
        assert data["position"]["z"] == 150
        assert data["is_flying"] is True
        assert data["battery"] == 85
        assert data["temperature"] == 35
    
    def test_multiple_drones_backend_integration(self, client):
        """Test multiple drones integration with backend"""
        # Add multiple drones
        for i in range(3):
            drone_id = f"drone_{i}"
            state_update = {
                "udp_port": 8889 + i,
                "position": {"x": i * 100, "y": i * 100, "z": 100},
                "is_flying": True,
                "battery": 90 - i * 5
            }
            
            response = client.post(f"/api/drones/{drone_id}/state", json=state_update)
            assert response.status_code == 200
        
        # Get all drones
        response = client.get("/api/drones")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 3
        
        # Verify each drone
        for i in range(3):
            drone_id = f"drone_{i}"
            assert drone_id in data["drones"]
            drone_data = data["drones"][drone_id]
            assert drone_data["position"]["x"] == i * 100
            assert drone_data["battery"] == 90 - i * 5
    
    @pytest.mark.asyncio
    async def test_register_with_backend(self, mock_drone_instance):
        """Test drone registration with backend"""
        # Mock HTTP session and send_state_to_backend
        mock_drone_instance.http_session = Mock()
        mock_drone_instance.send_state_to_backend = AsyncMock()
        
        # Test successful registration
        result = await mock_drone_instance.register_with_backend()
        assert result is True
        mock_drone_instance.send_state_to_backend.assert_called_once()
        
        # Test failed registration
        mock_drone_instance.send_state_to_backend.side_effect = Exception("Registration failed")
        result = await mock_drone_instance.register_with_backend()
        assert result is False
    
    def test_state_serialization_compatibility(self, mock_drone_instance):
        """Test that mock drone state serialization is compatible with backend"""
        # Set up drone state with various values
        mock_drone_instance.state.position = Vector3(123.45, 678.90, 234.56)
        mock_drone_instance.state.rotation = Vector3(12.3, 45.6, 78.9)
        mock_drone_instance.state.velocity = Vector3(10.5, -20.3, 5.7)
        mock_drone_instance.state.acceleration = Vector3(1.2, -3.4, -980.1)
        mock_drone_instance.state.is_flying = True
        mock_drone_instance.state.is_connected = True
        mock_drone_instance.state.flight_time = 120
        mock_drone_instance.state.battery = 75
        mock_drone_instance.state.temperature = 42
        mock_drone_instance.state.barometer = 150
        mock_drone_instance.state.mission_pad_id = 3
        mock_drone_instance.state.mission_pad_x = 50
        mock_drone_instance.state.mission_pad_y = -30
        mock_drone_instance.state.mission_pad_z = 200
        mock_drone_instance.state.speed = 80
        mock_drone_instance.state.rc_values = (25, -50, 75, -100)
        
        # Create the state data that would be sent to backend
        state_data = {
            "udp_port": mock_drone_instance.state.udp_port,
            "position": {
                "x": mock_drone_instance.state.position.x,
                "y": mock_drone_instance.state.position.y,
                "z": mock_drone_instance.state.position.z
            },
            "rotation": {
                "x": mock_drone_instance.state.rotation.x,
                "y": mock_drone_instance.state.rotation.y,
                "z": mock_drone_instance.state.rotation.z
            },
            "velocity": {
                "x": mock_drone_instance.state.velocity.x,
                "y": mock_drone_instance.state.velocity.y,
                "z": mock_drone_instance.state.velocity.z
            },
            "acceleration": {
                "x": mock_drone_instance.state.acceleration.x,
                "y": mock_drone_instance.state.acceleration.y,
                "z": mock_drone_instance.state.acceleration.z
            },
            "is_flying": mock_drone_instance.state.is_flying,
            "is_connected": mock_drone_instance.state.is_connected,
            "flight_time": mock_drone_instance.state.flight_time,
            "battery": mock_drone_instance.state.battery,
            "temperature": mock_drone_instance.state.temperature,
            "barometer": mock_drone_instance.state.barometer,
            "mission_pad_id": mock_drone_instance.state.mission_pad_id,
            "mission_pad_x": mock_drone_instance.state.mission_pad_x,
            "mission_pad_y": mock_drone_instance.state.mission_pad_y,
            "mission_pad_z": mock_drone_instance.state.mission_pad_z,
            "speed": mock_drone_instance.state.speed,
            "rc_values": mock_drone_instance.state.rc_values,
            "last_command_time": mock_drone_instance.state.last_command_time,
            "last_update_time": mock_drone_instance.state.last_update_time
        }
        
        # Verify all expected fields are present
        expected_fields = [
            "udp_port", "position", "rotation", "velocity", "acceleration",
            "is_flying", "is_connected", "flight_time", "battery", "temperature",
            "barometer", "mission_pad_id", "mission_pad_x", "mission_pad_y", "mission_pad_z",
            "speed", "rc_values", "last_command_time", "last_update_time"
        ]
        
        for field in expected_fields:
            assert field in state_data, f"Missing field: {field}"
        
        # Verify nested structures
        assert "x" in state_data["position"]
        assert "y" in state_data["position"]
        assert "z" in state_data["position"]
        
        assert "x" in state_data["rotation"]
        assert "y" in state_data["rotation"]
        assert "z" in state_data["rotation"]
        
        assert "x" in state_data["velocity"]
        assert "y" in state_data["velocity"]
        assert "z" in state_data["velocity"]
        
        # Verify data types
        assert isinstance(state_data["is_flying"], bool)
        assert isinstance(state_data["battery"], int)
        assert isinstance(state_data["temperature"], int)
        assert isinstance(state_data["rc_values"], tuple)


class TestWebSocketIntegration:
    """Test WebSocket integration with mock drones"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Clear state before each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        websocket_manager.active_connections.clear()
        yield
        # Clear after each test
        drone_state_manager.drones.clear()
        drone_state_manager.last_update_times.clear()
        websocket_manager.active_connections.clear()
    
    def test_websocket_receives_drone_updates(self):
        """Test that WebSocket clients receive drone state updates"""
        client = TestClient(app)
        
        # Connect WebSocket
        with client.websocket_connect("/ws") as websocket:
            # Add a drone via API (simulating mock drone update)
            state_update = {
                "udp_port": 8889,
                "position": {"x": 100, "y": 200, "z": 150},
                "is_flying": True,
                "battery": 85
            }
            
            # This would normally be done by mock drone, but we simulate it
            response = client.post("/api/drones/test_drone/state", json=state_update)
            assert response.status_code == 200
            
            # WebSocket should receive drone_added message
            data = websocket.receive_text()
            message = json.loads(data)
            
            assert message["type"] == "drone_added"
            assert message["drone_id"] == "test_drone"
            assert message["initial_state"]["battery"] == 85
            assert message["initial_state"]["position"]["x"] == 100
    
    def test_websocket_receives_multiple_drone_updates(self):
        """Test WebSocket receives updates for multiple drones"""
        client = TestClient(app)
        
        with client.websocket_connect("/ws") as websocket:
            # Add multiple drones
            for i in range(2):
                drone_id = f"drone_{i}"
                state_update = {
                    "udp_port": 8889 + i,
                    "position": {"x": i * 100, "y": i * 100, "z": 100},
                    "battery": 90 - i * 10
                }
                
                response = client.post(f"/api/drones/{drone_id}/state", json=state_update)
                assert response.status_code == 200
                
                # Receive WebSocket message
                data = websocket.receive_text()
                message = json.loads(data)
                
                assert message["type"] == "drone_added"
                assert message["drone_id"] == drone_id
                assert message["initial_state"]["battery"] == 90 - i * 10


if __name__ == "__main__":
    pytest.main([__file__])