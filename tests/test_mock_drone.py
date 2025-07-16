"""
Unit tests for MockDrone UDP server functionality
"""
import pytest
import asyncio
import socket
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_drone.mock_drone import MockDrone
from backend.models import DroneCommand


class TestMockDrone:
    """Test cases for MockDrone class"""
    
    @pytest.fixture
    def mock_drone(self):
        """Create a mock drone instance for testing"""
        return MockDrone("test_drone", 8890, "http://localhost:8000")
    
    def test_initialization(self, mock_drone):
        """Test mock drone initialization"""
        assert mock_drone.drone_id == "test_drone"
        assert mock_drone.udp_port == 8890
        assert mock_drone.backend_url == "http://localhost:8000"
        assert mock_drone.state.drone_id == "test_drone"
        assert mock_drone.state.udp_port == 8890
        assert not mock_drone.running
    
    def test_command_type_detection(self, mock_drone):
        """Test command type detection"""
        assert mock_drone.get_command_type("battery?") == "read"
        assert mock_drone.get_command_type("speed") == "setting"
        assert mock_drone.get_command_type("takeoff") == "control"
    
    def test_parameter_validation(self, mock_drone):
        """Test command parameter validation"""
        command = DroneCommand("control", "go", ["10", "20", "30", "50"], 0.0)
        assert mock_drone.validate_command_parameters(command, 4)
        assert not mock_drone.validate_command_parameters(command, 3)
    
    @pytest.mark.asyncio
    async def test_command_processing(self, mock_drone):
        """Test basic command processing"""
        # Test command mode
        response = await mock_drone.process_command("command")
        assert response == "ok"
        assert mock_drone.state.is_connected
        
        # Test battery query
        response = await mock_drone.process_command("battery?")
        assert response == "100"  # Default battery level
        
        # Test speed query
        response = await mock_drone.process_command("speed?")
        assert "x:0 y:0 z:0" in response
        
        # Test unknown command
        response = await mock_drone.process_command("unknown_command")
        assert response == "error"
    
    @pytest.mark.asyncio
    async def test_control_commands(self, mock_drone):
        """Test control commands"""
        # Enter command mode first
        await mock_drone.process_command("command")
        
        # Test takeoff
        response = await mock_drone.process_command("takeoff")
        assert response == "ok"
        assert mock_drone.state.is_flying
        assert mock_drone.state.position.z == 100
        
        # Test takeoff when already flying (should error)
        response = await mock_drone.process_command("takeoff")
        assert response == "error"
        
        # Test movement commands
        response = await mock_drone.process_command("up 50")
        assert response == "ok"
        assert mock_drone.state.position.z == 150
        
        response = await mock_drone.process_command("down 30")
        assert response == "ok"
        assert mock_drone.state.position.z == 120
        
        response = await mock_drone.process_command("left 40")
        assert response == "ok"
        assert mock_drone.state.position.x == -40
        
        response = await mock_drone.process_command("right 60")
        assert response == "ok"
        assert mock_drone.state.position.x == 20
        
        response = await mock_drone.process_command("forward 80")
        assert response == "ok"
        assert mock_drone.state.position.y == 80
        
        response = await mock_drone.process_command("back 30")
        assert response == "ok"
        assert mock_drone.state.position.y == 50
        
        # Test rotation
        response = await mock_drone.process_command("cw 90")
        assert response == "ok"
        assert mock_drone.state.rotation.z == 90
        
        response = await mock_drone.process_command("ccw 45")
        assert response == "ok"
        assert mock_drone.state.rotation.z == 45
        
        # Test land
        response = await mock_drone.process_command("land")
        assert response == "ok"
        assert not mock_drone.state.is_flying
        assert mock_drone.state.position.z == 0
    
    @pytest.mark.asyncio
    async def test_movement_parameter_validation(self, mock_drone):
        """Test movement command parameter validation"""
        await mock_drone.process_command("command")
        await mock_drone.process_command("takeoff")
        
        # Test invalid distances
        assert await mock_drone.process_command("up 10") == "error"  # Too small
        assert await mock_drone.process_command("up 600") == "error"  # Too large
        assert await mock_drone.process_command("down abc") == "error"  # Invalid format
        
        # Test missing parameters
        assert await mock_drone.process_command("up") == "error"
        assert await mock_drone.process_command("left") == "error"
    
    @pytest.mark.asyncio
    async def test_go_command(self, mock_drone):
        """Test go command"""
        await mock_drone.process_command("command")
        await mock_drone.process_command("takeoff")
        
        # Valid go command
        response = await mock_drone.process_command("go 100 200 50 80")
        assert response == "ok"
        assert mock_drone.state.position.x == 100
        assert mock_drone.state.position.y == 200
        assert mock_drone.state.position.z == 150  # 100 + 50
        
        # Invalid parameters
        assert await mock_drone.process_command("go 600 0 0 50") == "error"  # Out of range
        assert await mock_drone.process_command("go 100 200 50 5") == "error"  # Speed too low
        assert await mock_drone.process_command("go 100 200 50") == "error"  # Missing parameter
    
    @pytest.mark.asyncio
    async def test_curve_command(self, mock_drone):
        """Test curve command"""
        await mock_drone.process_command("command")
        await mock_drone.process_command("takeoff")
        
        # Valid curve command
        response = await mock_drone.process_command("curve 50 50 0 100 100 0 30")
        assert response == "ok"
        assert mock_drone.state.position.x == 100
        assert mock_drone.state.position.y == 100
        
        # Invalid parameters
        assert await mock_drone.process_command("curve 600 0 0 0 0 0 30") == "error"  # Out of range
        assert await mock_drone.process_command("curve 50 50 0 100 100 0 70") == "error"  # Speed too high
    
    @pytest.mark.asyncio
    async def test_flip_command(self, mock_drone):
        """Test flip command"""
        await mock_drone.process_command("command")
        
        # Test flip when not flying (should error)
        assert await mock_drone.process_command("flip l") == "error"
        
        await mock_drone.process_command("takeoff")
        
        # Valid flip commands
        assert await mock_drone.process_command("flip l") == "ok"
        assert await mock_drone.process_command("flip r") == "ok"
        assert await mock_drone.process_command("flip f") == "ok"
        assert await mock_drone.process_command("flip b") == "ok"
        
        # Invalid direction
        assert await mock_drone.process_command("flip x") == "error"
    
    @pytest.mark.asyncio
    async def test_setting_commands(self, mock_drone):
        """Test setting commands"""
        await mock_drone.process_command("command")
        
        # Test speed setting
        response = await mock_drone.process_command("speed 50")
        assert response == "ok"
        assert mock_drone.state.speed == 50
        
        # Invalid speed
        assert await mock_drone.process_command("speed 5") == "error"  # Too low
        assert await mock_drone.process_command("speed 150") == "error"  # Too high
        
        # Test RC setting
        response = await mock_drone.process_command("rc 50 -30 20 -10")
        assert response == "ok"
        assert mock_drone.state.rc_values == (50, -30, 20, -10)
        
        # Invalid RC values
        assert await mock_drone.process_command("rc 150 0 0 0") == "error"  # Out of range
        assert await mock_drone.process_command("rc 50 30 20") == "error"  # Missing parameter
        
        # Test WiFi setting
        response = await mock_drone.process_command("wifi TestSSID TestPass")
        assert response == "ok"
        
        # Test mission pad commands
        assert await mock_drone.process_command("mon") == "ok"
        assert await mock_drone.process_command("moff") == "ok"
        assert mock_drone.state.mission_pad_id == -1
        
        assert await mock_drone.process_command("mdirection 1") == "ok"
        assert await mock_drone.process_command("mdirection 3") == "error"  # Invalid direction
    
    @pytest.mark.asyncio
    async def test_read_commands(self, mock_drone):
        """Test read commands"""
        await mock_drone.process_command("command")
        
        # Test all read commands
        assert await mock_drone.process_command("battery?") == "100"
        assert await mock_drone.process_command("time?") == "0"
        assert "x:0 y:0 z:0" in await mock_drone.process_command("speed?")
        assert await mock_drone.process_command("wifi?") == "90"
        assert await mock_drone.process_command("sdk?") == "ok"
        assert "0TQZH77ED00" in await mock_drone.process_command("sn?")
        assert await mock_drone.process_command("hardware?") == "RMTT"
        assert await mock_drone.process_command("wifiversion?") == "1.3.0.0"
        assert "TELLO" in await mock_drone.process_command("ap?")
        assert "TELLO" in await mock_drone.process_command("ssid?")
    
    @pytest.mark.asyncio
    async def test_emergency_command(self, mock_drone):
        """Test emergency command"""
        await mock_drone.process_command("command")
        await mock_drone.process_command("takeoff")
        
        # Set some position and velocity
        mock_drone.state.position.x = 100
        mock_drone.state.position.y = 200
        mock_drone.state.velocity.x = 50
        
        # Emergency should reset everything
        response = await mock_drone.process_command("emergency")
        assert response == "ok"
        assert not mock_drone.state.is_flying
        assert mock_drone.state.position.z == 0
        assert mock_drone.state.velocity.x == 0
    
    @pytest.mark.asyncio
    async def test_motor_commands(self, mock_drone):
        """Test motor on/off commands"""
        await mock_drone.process_command("command")
        
        assert await mock_drone.process_command("motoron") == "ok"
        assert await mock_drone.process_command("motoroff") == "ok"
        assert await mock_drone.process_command("throwfly") == "ok"
        assert mock_drone.state.is_flying  # throwfly should enable flying
    
    @pytest.mark.asyncio
    async def test_invalid_commands(self, mock_drone):
        """Test handling of invalid commands"""
        # Empty command
        response = await mock_drone.process_command("")
        assert response == "error"
        
        # Command with invalid format
        response = await mock_drone.process_command("   ")
        assert response == "error"
    
    def test_command_handlers_setup(self, mock_drone):
        """Test that command handlers are properly set up"""
        # Control commands
        control_handlers = [
            'command', 'takeoff', 'land', 'emergency', 'up', 'down', 'left', 'right',
            'forward', 'back', 'cw', 'ccw', 'stop', 'flip', 'go', 'curve',
            'motoron', 'motoroff', 'throwfly'
        ]
        
        # Setting commands
        setting_handlers = ['speed', 'rc', 'wifi', 'mon', 'moff', 'mdirection']
        
        # Read commands
        read_handlers = [
            'speed?', 'battery?', 'time?', 'wifi?', 'sdk?', 'sn?',
            'hardware?', 'wifiversion?', 'ap?', 'ssid?'
        ]
        
        all_handlers = control_handlers + setting_handlers + read_handlers
        
        for handler in all_handlers:
            assert handler in mock_drone.command_handlers, f"Handler '{handler}' not found"
        
        # Verify total count
        assert len(mock_drone.command_handlers) == len(all_handlers)
    
    @pytest.mark.asyncio
    async def test_socket_creation_error_handling(self, mock_drone):
        """Test error handling during socket creation"""
        with patch('socket.socket') as mock_socket:
            mock_socket.side_effect = Exception("Socket creation failed")
            
            with pytest.raises(Exception, match="Socket creation failed"):
                await mock_drone.start_udp_server()


@pytest.mark.asyncio
async def test_udp_communication():
    """Integration test for UDP communication"""
    # This test requires an available port and actual socket communication
    test_port = 8891
    
    # Check if port is available
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('localhost', test_port))
        sock.close()
    except OSError:
        pytest.skip(f"Port {test_port} is not available for testing")
    
    # Create mock drone
    drone = MockDrone("test_drone", test_port)
    
    # Start server in background
    server_task = asyncio.create_task(drone.start_udp_server())
    
    # Give server time to start
    await asyncio.sleep(0.1)
    
    try:
        # Create client socket
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_sock.settimeout(1.0)
        
        # Send command
        client_sock.sendto(b"command", ('localhost', test_port))
        
        # Receive response
        response, _ = client_sock.recvfrom(1024)
        assert response.decode() == "ok"
        
        client_sock.close()
        
    finally:
        # Clean up
        await drone.stop()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    pytest.main([__file__])