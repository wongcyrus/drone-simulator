"""
Unit tests for PhysicsEngine realistic drone simulation
"""
import pytest
import time
import math
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_drone.physics_engine import PhysicsEngine
from backend.models import DroneState, Vector3, SimulationConfig


class TestPhysicsEngine:
    """Test cases for PhysicsEngine class"""
    
    @pytest.fixture
    def config(self):
        """Create a simulation config for testing"""
        return SimulationConfig(
            update_rate=30,
            gravity=9.81,
            air_resistance=0.1,
            max_acceleration=500,
            battery_drain_rate=0.1,
            scene_bounds=(1000, 1000, 500)
        )
    
    @pytest.fixture
    def physics_engine(self, config):
        """Create a physics engine instance for testing"""
        return PhysicsEngine(config)
    
    @pytest.fixture
    def drone_state(self):
        """Create a drone state for testing"""
        return DroneState(
            drone_id="test_drone",
            udp_port=8889,
            position=Vector3(0, 0, 0),
            rotation=Vector3(0, 0, 0),
            velocity=Vector3(0, 0, 0)
        )
    
    def test_initialization(self, physics_engine, config):
        """Test physics engine initialization"""
        assert physics_engine.config == config
        assert physics_engine.gravity == config.gravity
        assert physics_engine.air_resistance == config.air_resistance
        assert physics_engine.max_acceleration == config.max_acceleration
        assert physics_engine.takeoff_speed == 50
        assert physics_engine.landing_speed == 30
        assert physics_engine.hover_height == 100
        assert len(physics_engine.animations) == 0
    
    def test_takeoff_animation(self, physics_engine, drone_state):
        """Test takeoff animation"""
        # Start takeoff animation
        physics_engine.start_takeoff_animation(drone_state)
        
        assert drone_state.is_flying
        assert drone_state.drone_id in physics_engine.animations
        
        animation = physics_engine.animations[drone_state.drone_id]
        assert animation['type'] == 'takeoff'
        assert animation['target_height'] == 100
        assert animation['start_position'].z == 0
    
    def test_landing_animation(self, physics_engine, drone_state):
        """Test landing animation"""
        # Set drone to flying state at some height
        drone_state.is_flying = True
        drone_state.position.z = 150
        
        # Start landing animation
        physics_engine.start_landing_animation(drone_state)
        
        assert drone_state.drone_id in physics_engine.animations
        
        animation = physics_engine.animations[drone_state.drone_id]
        assert animation['type'] == 'landing'
        assert animation['target_height'] == 0
        assert animation['start_position'].z == 150
    
    def test_movement_animation(self, physics_engine, drone_state):
        """Test movement animation"""
        drone_state.is_flying = True
        target_position = Vector3(100, 200, 150)
        speed = 50
        
        physics_engine.start_movement_animation(drone_state, target_position, speed)
        
        assert drone_state.drone_id in physics_engine.animations
        
        animation = physics_engine.animations[drone_state.drone_id]
        assert animation['type'] == 'linear'
        assert animation['target_position'] == target_position
        assert animation['speed'] == speed
    
    def test_flip_animation(self, physics_engine, drone_state):
        """Test flip animation"""
        drone_state.is_flying = True
        
        # Test different flip directions
        for direction in ['l', 'r', 'f', 'b']:
            physics_engine.start_flip_animation(drone_state, direction)
            
            assert drone_state.drone_id in physics_engine.animations
            
            animation = physics_engine.animations[drone_state.drone_id]
            assert animation['type'] == 'flip'
            assert animation['axis'] in ['x', 'y']
            assert abs(animation['rotation_amount']) == 360
            
            # Clear animation for next test
            del physics_engine.animations[drone_state.drone_id]
    
    def test_rotation_animation(self, physics_engine, drone_state):
        """Test rotation animation"""
        target_yaw = 90
        
        physics_engine.start_rotation_animation(drone_state, target_yaw)
        
        assert drone_state.drone_id in physics_engine.animations
        
        animation = physics_engine.animations[drone_state.drone_id]
        assert animation['type'] == 'rotation'
        assert animation['target_yaw'] == target_yaw
        assert animation['start_yaw'] == 0
    
    def test_physics_update_basic(self, physics_engine, drone_state):
        """Test basic physics update"""
        dt = 1.0 / 30.0  # 30 FPS
        
        # Set some initial velocity
        drone_state.velocity = Vector3(10, 20, 30)
        initial_position = Vector3(drone_state.position.x, drone_state.position.y, drone_state.position.z)
        
        physics_engine.update_drone_physics(drone_state, dt)
        
        # Position should be updated based on velocity
        expected_x = initial_position.x + 10 * dt
        expected_y = initial_position.y + 20 * dt
        expected_z = initial_position.z + 30 * dt
        
        assert abs(drone_state.position.x - expected_x) < 0.01
        assert abs(drone_state.position.y - expected_y) < 0.01
        assert abs(drone_state.position.z - expected_z) < 0.01
    
    def test_gravity_application(self, physics_engine, drone_state):
        """Test gravity application"""
        dt = 1.0 / 30.0
        drone_state.is_flying = True
        initial_velocity_z = drone_state.velocity.z
        
        physics_engine.update_drone_physics(drone_state, dt)
        
        # Gravity should reduce vertical velocity
        gravity_cm = physics_engine.gravity * 100  # Convert to cm/s²
        expected_velocity_z = initial_velocity_z - gravity_cm * dt
        
        assert abs(drone_state.velocity.z - expected_velocity_z) < 0.01
    
    def test_air_resistance(self, physics_engine, drone_state):
        """Test air resistance application"""
        dt = 1.0 / 30.0
        drone_state.velocity = Vector3(100, 100, 100)
        
        physics_engine.update_drone_physics(drone_state, dt)
        
        # Air resistance should reduce velocity
        resistance_factor = 1.0 - (physics_engine.air_resistance * dt)
        expected_velocity = 100 * resistance_factor
        
        assert abs(drone_state.velocity.x - expected_velocity) < 0.01
        assert abs(drone_state.velocity.y - expected_velocity) < 0.01
        assert abs(drone_state.velocity.z - expected_velocity) < 0.01
    
    def test_boundary_constraints(self, physics_engine, drone_state):
        """Test scene boundary constraints"""
        bounds = physics_engine.config.scene_bounds
        
        # Test X boundary
        drone_state.position.x = bounds[0] / 2 + 100  # Beyond boundary
        drone_state.velocity.x = 50
        
        physics_engine.update_drone_physics(drone_state, 0.1)
        
        assert drone_state.position.x == bounds[0] / 2
        assert drone_state.velocity.x == 0
        
        # Test Y boundary
        drone_state.position.y = -bounds[1] / 2 - 100  # Beyond boundary
        drone_state.velocity.y = -50
        
        physics_engine.update_drone_physics(drone_state, 0.1)
        
        assert drone_state.position.y == -bounds[1] / 2
        assert drone_state.velocity.y == 0
        
        # Test Z boundary (ground)
        drone_state.position.z = -10  # Below ground
        drone_state.is_flying = True
        
        physics_engine.update_drone_physics(drone_state, 0.1)
        
        assert drone_state.position.z == 0
        assert not drone_state.is_flying
    
    def test_takeoff_animation_progress(self, physics_engine, drone_state):
        """Test takeoff animation progress over time"""
        physics_engine.start_takeoff_animation(drone_state)
        
        # Simulate animation progress
        dt = 1.0 / 30.0
        
        # Update physics multiple times
        for _ in range(10):
            physics_engine.update_drone_physics(drone_state, dt)
        
        # Drone should be moving upward
        assert drone_state.position.z > 0
        assert drone_state.is_flying
    
    def test_landing_animation_progress(self, physics_engine, drone_state):
        """Test landing animation progress over time"""
        drone_state.is_flying = True
        drone_state.position.z = 100
        
        physics_engine.start_landing_animation(drone_state)
        
        # Simulate animation progress
        dt = 1.0 / 30.0
        
        # Update physics multiple times
        for _ in range(50):  # More iterations for landing
            physics_engine.update_drone_physics(drone_state, dt)
        
        # Drone should be on ground and not flying
        assert drone_state.position.z == 0
        assert not drone_state.is_flying
    
    def test_animation_completion(self, physics_engine, drone_state):
        """Test animation completion and cleanup"""
        target_position = Vector3(100, 100, 100)
        physics_engine.start_movement_animation(drone_state, target_position, 100)
        
        # Simulate long enough time for animation to complete
        dt = 1.0
        physics_engine.update_drone_physics(drone_state, dt)
        
        # Animation should be completed and removed
        assert drone_state.drone_id not in physics_engine.animations
        assert drone_state.position.x == target_position.x
        assert drone_state.position.y == target_position.y
        assert drone_state.position.z == target_position.z
    
    def test_smooth_step_function(self, physics_engine):
        """Test smooth step easing function"""
        # Test boundary values
        assert physics_engine._smooth_step(0.0) == 0.0
        assert physics_engine._smooth_step(1.0) == 1.0
        
        # Test middle value
        mid_value = physics_engine._smooth_step(0.5)
        assert 0.0 < mid_value < 1.0
        assert mid_value == 0.5  # Should be 0.5 for input 0.5
    
    def test_distance_calculation(self, physics_engine):
        """Test 3D distance calculation"""
        pos1 = Vector3(0, 0, 0)
        pos2 = Vector3(3, 4, 0)
        
        distance = physics_engine._calculate_distance(pos1, pos2)
        assert distance == 5.0  # 3-4-5 triangle
        
        pos3 = Vector3(1, 1, 1)
        pos4 = Vector3(4, 5, 5)
        
        distance = physics_engine._calculate_distance(pos3, pos4)
        expected = math.sqrt(3*3 + 4*4 + 4*4)  # sqrt(9 + 16 + 16) = sqrt(41)
        assert abs(distance - expected) < 0.01
    
    def test_vector_normalization(self, physics_engine):
        """Test vector normalization"""
        vector = Vector3(3, 4, 0)
        normalized = physics_engine._normalize_vector(vector)
        
        # Length should be 1
        length = math.sqrt(normalized.x**2 + normalized.y**2 + normalized.z**2)
        assert abs(length - 1.0) < 0.01
        
        # Direction should be preserved
        assert abs(normalized.x - 0.6) < 0.01  # 3/5
        assert abs(normalized.y - 0.8) < 0.01  # 4/5
        assert normalized.z == 0.0
    
    def test_cubic_bezier(self, physics_engine):
        """Test cubic Bezier interpolation"""
        # Test boundary values
        result = physics_engine._cubic_bezier(0.0, 0, 1, 2, 3)
        assert result == 0
        
        result = physics_engine._cubic_bezier(1.0, 0, 1, 2, 3)
        assert result == 3
        
        # Test middle value
        result = physics_engine._cubic_bezier(0.5, 0, 1, 2, 3)
        assert 0 < result < 3
    
    def test_animation_state_queries(self, physics_engine, drone_state):
        """Test animation state query methods"""
        drone_id = drone_state.drone_id
        
        # Initially no animation
        assert not physics_engine.is_animating(drone_id)
        
        # Start animation
        physics_engine.start_takeoff_animation(drone_state)
        assert physics_engine.is_animating(drone_id)
        
        # Stop animation
        physics_engine.stop_animation(drone_id)
        assert not physics_engine.is_animating(drone_id)
        assert drone_id not in physics_engine.animations
    
    def test_multiple_drone_animations(self, physics_engine):
        """Test handling multiple drone animations simultaneously"""
        drone1 = DroneState("drone1", 8889)
        drone2 = DroneState("drone2", 8890)
        
        # Start different animations for each drone
        physics_engine.start_takeoff_animation(drone1)
        physics_engine.start_landing_animation(drone2)
        
        assert len(physics_engine.animations) == 2
        assert physics_engine.is_animating("drone1")
        assert physics_engine.is_animating("drone2")
        
        # Animations should be independent
        assert physics_engine.animations["drone1"]["type"] == "takeoff"
        assert physics_engine.animations["drone2"]["type"] == "landing"


if __name__ == "__main__":
    pytest.main([__file__])