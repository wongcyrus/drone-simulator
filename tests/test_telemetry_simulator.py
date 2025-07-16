"""
Unit tests for TelemetrySimulator realistic sensor data generation
"""
import pytest
import time
import math
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_drone.telemetry_simulator import TelemetrySimulator
from backend.models import DroneState, Vector3, SimulationConfig


class TestTelemetrySimulator:
    """Test cases for TelemetrySimulator class"""
    
    @pytest.fixture
    def config(self):
        """Create a simulation config for testing"""
        return SimulationConfig(
            update_rate=30,
            battery_drain_rate=0.5,  # Higher drain for testing
            scene_bounds=(1000, 1000, 500)
        )
    
    @pytest.fixture
    def telemetry_simulator(self, config):
        """Create a telemetry simulator instance for testing"""
        return TelemetrySimulator(config)
    
    @pytest.fixture
    def drone_state(self):
        """Create a drone state for testing"""
        return DroneState(
            drone_id="test_drone",
            udp_port=8889,
            position=Vector3(0, 0, 100),
            rotation=Vector3(0, 0, 0),
            velocity=Vector3(0, 0, 0),
            battery=100,
            temperature=25
        )
    
    def test_initialization(self, telemetry_simulator, config):
        """Test telemetry simulator initialization"""
        assert telemetry_simulator.config == config
        assert telemetry_simulator.base_temperature == 25
        assert telemetry_simulator.temperature_variance == 5
        assert telemetry_simulator.initial_battery == 100
        assert len(telemetry_simulator.mission_pads) == 8  # Default mission pads
        assert telemetry_simulator.mission_pad_detection_range == 200
        assert telemetry_simulator.position_noise == 2.0
        assert telemetry_simulator.velocity_noise == 1.0
        assert telemetry_simulator.rotation_noise == 1.0
        assert telemetry_simulator.acceleration_noise == 5.0
    
    def test_mission_pad_initialization(self, telemetry_simulator):
        """Test mission pad initialization"""
        mission_pads = telemetry_simulator.get_mission_pad_positions()
        
        # Should have 8 default mission pads
        assert len(mission_pads) == 8
        
        # Check specific positions
        assert mission_pads[1] == Vector3(100, 100, 0)
        assert mission_pads[2] == Vector3(-100, 100, 0)
        assert mission_pads[3] == Vector3(100, -100, 0)
        assert mission_pads[4] == Vector3(-100, -100, 0)
    
    def test_battery_drain_basic(self, telemetry_simulator, drone_state):
        """Test basic battery drain"""
        initial_battery = drone_state.battery
        dt = 1.0  # 1 second
        
        # Update telemetry
        telemetry_simulator.update_telemetry(drone_state, dt)
        
        # Battery should have drained
        assert drone_state.battery < initial_battery
    
    def test_battery_drain_flying_vs_grounded(self, telemetry_simulator, drone_state):
        """Test battery drains faster when flying"""
        # Test grounded drone
        drone_state.is_flying = False
        initial_battery = drone_state.battery
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        grounded_drain = initial_battery - drone_state.battery
        
        # Reset battery and test flying drone
        drone_state.battery = initial_battery
        drone_state.is_flying = True
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        flying_drain = initial_battery - drone_state.battery
        
        # Flying should drain more battery
        assert flying_drain > grounded_drain
    
    def test_battery_drain_with_movement(self, telemetry_simulator, drone_state):
        """Test battery drains more with movement"""
        drone_state.is_flying = True
        
        # Test stationary drone
        drone_state.velocity = Vector3(0, 0, 0)
        initial_battery = drone_state.battery
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        stationary_drain = initial_battery - drone_state.battery
        
        # Reset battery and test moving drone
        drone_state.battery = initial_battery
        drone_state.velocity = Vector3(50, 50, 20)  # Fast movement
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        moving_drain = initial_battery - drone_state.battery
        
        # Moving should drain more battery
        assert moving_drain > stationary_drain
    
    def test_battery_critical_level(self, telemetry_simulator, drone_state):
        """Test emergency landing at critical battery level"""
        drone_state.is_flying = True
        drone_state.position.z = 150
        drone_state.battery = 3  # Critical level
        
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Should trigger emergency landing
        assert not drone_state.is_flying
        assert drone_state.position.z == 0
    
    def test_temperature_simulation(self, telemetry_simulator, drone_state):
        """Test temperature simulation"""
        initial_temp = drone_state.temperature
        
        # Test grounded drone
        drone_state.is_flying = False
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        grounded_temp = drone_state.temperature
        
        # Test flying drone
        drone_state.is_flying = True
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        flying_temp = drone_state.temperature
        
        # Flying should generally increase temperature
        # (though there's randomness, so we test multiple times)
        temp_increases = 0
        for _ in range(10):
            drone_state.temperature = 25
            drone_state.is_flying = True
            telemetry_simulator.update_telemetry(drone_state, 1.0)
            if drone_state.temperature > 25:
                temp_increases += 1
        
        # Most of the time, flying should increase temperature
        assert temp_increases > 5
    
    def test_temperature_altitude_effect(self, telemetry_simulator, drone_state):
        """Test temperature decreases with altitude"""
        drone_state.is_flying = True
        
        # Test at ground level
        drone_state.position.z = 0
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        ground_temp = drone_state.temperature
        
        # Test at high altitude
        drone_state.position.z = 500  # 5 meters high
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        high_temp = drone_state.temperature
        
        # Higher altitude should generally be cooler
        # Test multiple times due to randomness
        cooler_count = 0
        for _ in range(10):
            drone_state.position.z = 0
            telemetry_simulator.update_telemetry(drone_state, 1.0)
            ground_temp = drone_state.temperature
            
            drone_state.position.z = 500
            telemetry_simulator.update_telemetry(drone_state, 1.0)
            high_temp = drone_state.temperature
            
            if high_temp <= ground_temp:
                cooler_count += 1
        
        # Should be cooler at altitude most of the time
        assert cooler_count > 3
    
    def test_barometer_simulation(self, telemetry_simulator, drone_state):
        """Test barometer readings based on altitude"""
        # Test at different altitudes
        altitudes = [0, 100, 200, 300, 500]
        
        for altitude in altitudes:
            drone_state.position.z = altitude
            telemetry_simulator.update_telemetry(drone_state, 1.0)
            
            # Barometer should roughly correspond to altitude
            # Allow for noise in the reading
            assert abs(drone_state.barometer - altitude) < 50
    
    def test_acceleration_simulation(self, telemetry_simulator, drone_state):
        """Test acceleration simulation"""
        dt = 1.0 / 30.0  # 30 FPS
        
        # Test flying drone (should have gravity component)
        drone_state.is_flying = True
        drone_state.velocity = Vector3(0, 0, 0)  # Hovering
        
        telemetry_simulator.update_telemetry(drone_state, dt)
        
        # Should have some acceleration values
        assert drone_state.acceleration.x != 0 or drone_state.acceleration.y != 0 or drone_state.acceleration.z != 0
        
        # Z acceleration should generally be negative due to gravity when flying
        # Test multiple times due to randomness
        negative_z_count = 0
        for _ in range(10):
            drone_state.is_flying = True
            telemetry_simulator.update_telemetry(drone_state, dt)
            if drone_state.acceleration.z < 0:
                negative_z_count += 1
        
        assert negative_z_count > 5  # Most readings should show gravity effect
    
    def test_mission_pad_detection(self, telemetry_simulator, drone_state):
        """Test mission pad detection"""
        # Position drone near mission pad 1 (100, 100, 0)
        drone_state.position = Vector3(105, 95, 150)  # Close to pad 1
        drone_state.is_flying = True
        
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Should detect mission pad 1
        assert drone_state.mission_pad_id == 1
        assert abs(drone_state.mission_pad_x - 5) < 10  # Allow for noise
        assert abs(drone_state.mission_pad_y - (-5)) < 10  # Allow for noise
        assert drone_state.mission_pad_z > 0
    
    def test_mission_pad_detection_range(self, telemetry_simulator, drone_state):
        """Test mission pad detection range limits"""
        # Position drone far from any mission pad
        drone_state.position = Vector3(500, 500, 150)
        drone_state.is_flying = True
        
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Should not detect any mission pad
        assert drone_state.mission_pad_id == -1
        assert drone_state.mission_pad_x == -100
        assert drone_state.mission_pad_y == -100
        assert drone_state.mission_pad_z == -100
    
    def test_mission_pad_altitude_limits(self, telemetry_simulator, drone_state):
        """Test mission pad detection altitude limits"""
        # Position drone at correct X,Y but too high
        drone_state.position = Vector3(100, 100, 400)  # Too high
        drone_state.is_flying = True
        
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Should not detect mission pad due to altitude
        assert drone_state.mission_pad_id == -1
        
        # Test at reasonable altitude
        drone_state.position.z = 150  # Reasonable altitude
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Should detect mission pad now
        assert drone_state.mission_pad_id == 1
    
    def test_sensor_noise_application(self, telemetry_simulator, drone_state):
        """Test that sensor noise is applied"""
        original_position = Vector3(drone_state.position.x, drone_state.position.y, drone_state.position.z)
        original_velocity = Vector3(drone_state.velocity.x, drone_state.velocity.y, drone_state.velocity.z)
        original_rotation = Vector3(drone_state.rotation.x, drone_state.rotation.y, drone_state.rotation.z)
        
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Position should have some noise (test multiple times)
        position_changed = False
        for _ in range(10):
            drone_state.position = Vector3(100, 100, 100)
            telemetry_simulator._add_sensor_noise(drone_state)
            if (drone_state.position.x != 100 or 
                drone_state.position.y != 100 or 
                drone_state.position.z != 100):
                position_changed = True
                break
        
        assert position_changed
    
    def test_tello_state_string_generation(self, telemetry_simulator, drone_state):
        """Test Tello state string generation"""
        # Set up drone state
        drone_state.mission_pad_id = 1
        drone_state.mission_pad_x = 10
        drone_state.mission_pad_y = -5
        drone_state.mission_pad_z = 150
        drone_state.rotation = Vector3(5, -3, 90)
        drone_state.velocity = Vector3(20, -10, 5)
        drone_state.temperature = 35
        drone_state.position.z = 150
        drone_state.battery = 85
        drone_state.flight_time = 120
        drone_state.acceleration = Vector3(10, -5, -980)
        
        state_string = telemetry_simulator.get_tello_state_string(drone_state)
        
        # Check that state string contains expected values
        assert "mid:1" in state_string
        assert "x:10" in state_string
        assert "y:-5" in state_string
        assert "z:150" in state_string
        assert "mpry:5;-3;90" in state_string
        assert "vgx:20" in state_string
        assert "vgy:-10" in state_string
        assert "vgz:5" in state_string
        assert "bat:85" in state_string
        assert "time:120" in state_string
        assert "agx:10" in state_string
        assert "agy:-5" in state_string
        assert "agz:-980" in state_string
    
    def test_tello_state_string_no_mission_pad(self, telemetry_simulator, drone_state):
        """Test Tello state string when no mission pad is detected"""
        drone_state.mission_pad_id = -1
        
        state_string = telemetry_simulator.get_tello_state_string(drone_state)
        
        # Should show no mission pad detected
        assert "mid:-2" in state_string
        assert "x:-200" in state_string
        assert "y:-200" in state_string
        assert "z:-200" in state_string
    
    def test_sensor_failure_simulation(self, telemetry_simulator, drone_state):
        """Test sensor failure simulation"""
        # Test battery sensor failure
        telemetry_simulator.simulate_sensor_failure(drone_state, "battery")
        assert drone_state.battery == 0
        
        # Test temperature sensor failure
        telemetry_simulator.simulate_sensor_failure(drone_state, "temperature")
        assert drone_state.temperature == -1
        
        # Test barometer sensor failure
        telemetry_simulator.simulate_sensor_failure(drone_state, "barometer")
        assert drone_state.barometer == -1
        
        # Test mission pad sensor failure
        drone_state.mission_pad_id = 1
        telemetry_simulator.simulate_sensor_failure(drone_state, "mission_pad")
        assert drone_state.mission_pad_id == -1
        
        # Test acceleration sensor failure
        telemetry_simulator.simulate_sensor_failure(drone_state, "acceleration")
        assert drone_state.acceleration.x == 0
        assert drone_state.acceleration.y == 0
        assert drone_state.acceleration.z == 0
    
    def test_mission_pad_management(self, telemetry_simulator):
        """Test mission pad addition and removal"""
        # Add custom mission pad
        custom_position = Vector3(300, 300, 0)
        telemetry_simulator.add_mission_pad(9, custom_position)
        
        mission_pads = telemetry_simulator.get_mission_pad_positions()
        assert 9 in mission_pads
        assert mission_pads[9] == custom_position
        
        # Remove mission pad
        telemetry_simulator.remove_mission_pad(9)
        mission_pads = telemetry_simulator.get_mission_pad_positions()
        assert 9 not in mission_pads
    
    def test_detection_range_setting(self, telemetry_simulator):
        """Test mission pad detection range setting"""
        # Set custom detection range
        telemetry_simulator.set_detection_range(150)
        assert telemetry_simulator.mission_pad_detection_range == 150
        
        # Test range limits
        telemetry_simulator.set_detection_range(10)  # Too small
        assert telemetry_simulator.mission_pad_detection_range == 50  # Minimum
        
        telemetry_simulator.set_detection_range(1000)  # Too large
        assert telemetry_simulator.mission_pad_detection_range == 500  # Maximum
    
    def test_battery_reset(self, telemetry_simulator, drone_state):
        """Test battery reset functionality"""
        # Drain battery
        drone_state.battery = 20
        
        # Reset to full
        telemetry_simulator.reset_battery(drone_state, 100)
        assert drone_state.battery == 100
        
        # Reset to specific level
        telemetry_simulator.reset_battery(drone_state, 75)
        assert drone_state.battery == 75
        
        # Test bounds
        telemetry_simulator.reset_battery(drone_state, 150)  # Too high
        assert drone_state.battery == 100  # Clamped to maximum
        
        telemetry_simulator.reset_battery(drone_state, -10)  # Too low
        assert drone_state.battery == 0  # Clamped to minimum
    
    def test_telemetry_update_integration(self, telemetry_simulator, drone_state):
        """Test complete telemetry update integration"""
        # Set up initial state
        drone_state.is_flying = True
        drone_state.position = Vector3(100, 100, 150)  # Near mission pad 1
        drone_state.velocity = Vector3(30, 20, 10)
        initial_battery = drone_state.battery
        
        # Update telemetry
        telemetry_simulator.update_telemetry(drone_state, 1.0)
        
        # Verify all systems were updated
        assert drone_state.battery < initial_battery  # Battery drained
        assert drone_state.temperature > 0  # Temperature updated
        assert drone_state.barometer > 0  # Barometer updated
        assert drone_state.mission_pad_id == 1  # Mission pad detected
        assert drone_state.acceleration.x != 0 or drone_state.acceleration.y != 0 or drone_state.acceleration.z != 0  # Acceleration updated


if __name__ == "__main__":
    pytest.main([__file__])