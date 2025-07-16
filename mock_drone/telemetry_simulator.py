"""
Telemetry data simulation for realistic sensor readings and drone state information
"""
import random
import math
import time
from typing import Tuple, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import DroneState, Vector3, SimulationConfig


class TelemetrySimulator:
    """Generates realistic telemetry data for simulated drone sensors"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        
        # Telemetry parameters
        self.base_temperature = 25  # Base temperature in Celsius
        self.temperature_variance = 5  # Temperature variance range
        self.battery_start_time = time.time()
        self.initial_battery = 100
        
        # Mission pad simulation
        self.mission_pads = self._initialize_mission_pads()
        self.mission_pad_detection_range = 200  # cm
        
        # Sensor noise parameters
        self.position_noise = 2.0  # cm
        self.velocity_noise = 1.0  # cm/s
        self.rotation_noise = 1.0  # degrees
        self.acceleration_noise = 5.0  # cm/s²
        
        # Barometer simulation
        self.sea_level_pressure = 1013.25  # hPa
        self.pressure_altitude_factor = 0.12  # hPa per meter
    
    def _initialize_mission_pads(self) -> dict:
        """Initialize mission pad positions in the scene"""
        return {
            1: Vector3(100, 100, 0),
            2: Vector3(-100, 100, 0),
            3: Vector3(100, -100, 0),
            4: Vector3(-100, -100, 0),
            5: Vector3(0, 200, 0),
            6: Vector3(200, 0, 0),
            7: Vector3(0, -200, 0),
            8: Vector3(-200, 0, 0)
        }
    
    def update_telemetry(self, drone_state: DroneState, dt: float) -> None:
        """Update all telemetry data for the drone"""
        self._update_battery(drone_state, dt)
        self._update_temperature(drone_state)
        self._update_barometer(drone_state)
        self._update_acceleration(drone_state, dt)
        self._update_mission_pad_detection(drone_state)
        self._add_sensor_noise(drone_state)
    
    def _update_battery(self, drone_state: DroneState, dt: float) -> None:
        """Update battery level based on usage"""
        if drone_state.battery <= 0:
            return
        
        # Base drain rate
        base_drain = self.config.battery_drain_rate * (dt / 60.0)  # per minute to per second
        
        # Additional drain based on activity
        activity_multiplier = 1.0
        
        if drone_state.is_flying:
            activity_multiplier += 0.5  # Flying uses more battery
        
        # Movement increases battery drain
        velocity_magnitude = math.sqrt(
            drone_state.velocity.x**2 + 
            drone_state.velocity.y**2 + 
            drone_state.velocity.z**2
        )
        if velocity_magnitude > 10:  # Moving faster than 10 cm/s
            activity_multiplier += velocity_magnitude / 100.0
        
        # Calculate total drain
        total_drain = base_drain * activity_multiplier
        
        # Add some randomness
        total_drain *= random.uniform(0.8, 1.2)
        
        # Update battery
        drone_state.battery = max(0, int(drone_state.battery - total_drain))
        
        # Emergency landing if battery is critically low
        if drone_state.battery <= 5 and drone_state.is_flying:
            drone_state.is_flying = False
            drone_state.position.z = 0
    
    def _update_temperature(self, drone_state: DroneState) -> None:
        """Update temperature based on activity and environment"""
        # Base temperature with some variation
        base_temp = self.base_temperature + random.uniform(-2, 2)
        
        # Temperature increases with activity
        if drone_state.is_flying:
            base_temp += random.uniform(2, 8)
        
        # Altitude affects temperature (cooler at higher altitudes)
        altitude_effect = -0.006 * drone_state.position.z  # 0.6°C per 100m
        
        # Battery level affects temperature (lower battery = cooler)
        battery_effect = (drone_state.battery / 100.0) * 5
        
        # Calculate final temperature
        final_temp = base_temp + altitude_effect + battery_effect
        
        # Add some noise and clamp to reasonable range
        final_temp += random.uniform(-1, 1)
        drone_state.temperature = max(0, min(80, int(final_temp)))
    
    def _update_barometer(self, drone_state: DroneState) -> None:
        """Update barometer reading based on altitude"""
        # Convert altitude from cm to meters
        altitude_m = drone_state.position.z / 100.0
        
        # Calculate pressure based on altitude
        # Using simplified barometric formula
        pressure = self.sea_level_pressure * math.exp(-altitude_m / 8400)
        
        # Convert to height in cm (barometer reading)
        # This is a simplified conversion for simulation
        barometer_height = int(altitude_m * 100)  # Convert back to cm
        
        # Add some noise
        barometer_height += random.randint(-5, 5)
        
        drone_state.barometer = max(0, barometer_height)
    
    def _update_acceleration(self, drone_state: DroneState, dt: float) -> None:
        """Update acceleration readings based on movement"""
        if dt <= 0:
            return
        
        # Calculate acceleration from velocity changes
        # This is a simplified simulation - real drones would have IMU data
        
        # Gravity component (always present when flying)
        gravity_z = -981 if drone_state.is_flying else 0  # cm/s² (gravity)
        
        # Movement acceleration (simplified)
        velocity_magnitude = math.sqrt(
            drone_state.velocity.x**2 + 
            drone_state.velocity.y**2 + 
            drone_state.velocity.z**2
        )
        
        # Simulate acceleration based on movement
        if velocity_magnitude > 5:  # Moving
            # Random acceleration values during movement
            accel_x = random.uniform(-50, 50)
            accel_y = random.uniform(-50, 50)
            accel_z = random.uniform(-30, 30) + gravity_z
        else:  # Hovering or stationary
            # Small random values for hovering
            accel_x = random.uniform(-10, 10)
            accel_y = random.uniform(-10, 10)
            accel_z = random.uniform(-5, 5) + gravity_z
        
        # Update acceleration with some smoothing
        smoothing_factor = 0.7
        drone_state.acceleration.x = (
            smoothing_factor * drone_state.acceleration.x + 
            (1 - smoothing_factor) * accel_x
        )
        drone_state.acceleration.y = (
            smoothing_factor * drone_state.acceleration.y + 
            (1 - smoothing_factor) * accel_y
        )
        drone_state.acceleration.z = (
            smoothing_factor * drone_state.acceleration.z + 
            (1 - smoothing_factor) * accel_z
        )
    
    def _update_mission_pad_detection(self, drone_state: DroneState) -> None:
        """Update mission pad detection based on drone position"""
        closest_pad_id = -1
        closest_distance = float('inf')
        closest_pad_pos = None
        
        # Check distance to all mission pads
        for pad_id, pad_position in self.mission_pads.items():
            # Calculate 2D distance (mission pads are on the ground)
            distance = math.sqrt(
                (drone_state.position.x - pad_position.x)**2 + 
                (drone_state.position.y - pad_position.y)**2
            )
            
            # Check if within detection range and altitude is reasonable
            if (distance < self.mission_pad_detection_range and 
                20 <= drone_state.position.z <= 300):  # Reasonable detection altitude
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_pad_id = pad_id
                    closest_pad_pos = pad_position
        
        # Update mission pad detection
        if closest_pad_id != -1:
            drone_state.mission_pad_id = closest_pad_id
            
            # Calculate relative position to mission pad
            drone_state.mission_pad_x = int(drone_state.position.x - closest_pad_pos.x)
            drone_state.mission_pad_y = int(drone_state.position.y - closest_pad_pos.y)
            drone_state.mission_pad_z = int(drone_state.position.z)
            
            # Add some detection noise
            drone_state.mission_pad_x += random.randint(-5, 5)
            drone_state.mission_pad_y += random.randint(-5, 5)
            drone_state.mission_pad_z += random.randint(-3, 3)
        else:
            # No mission pad detected
            drone_state.mission_pad_id = -1
            drone_state.mission_pad_x = -100
            drone_state.mission_pad_y = -100
            drone_state.mission_pad_z = -100
    
    def _add_sensor_noise(self, drone_state: DroneState) -> None:
        """Add realistic sensor noise to readings"""
        # NOTE: We don't add noise to actual position/velocity/rotation as this would cause
        # unwanted movement. Instead, noise should be added only when reporting sensor values
        # to external systems (like in get_tello_state_string method).
        
        # Only add noise to acceleration readings as these are sensor-specific
        drone_state.acceleration.x += random.uniform(-self.acceleration_noise, self.acceleration_noise)
        drone_state.acceleration.y += random.uniform(-self.acceleration_noise, self.acceleration_noise)
        drone_state.acceleration.z += random.uniform(-self.acceleration_noise, self.acceleration_noise)
    
    def get_tello_state_string(self, drone_state: DroneState) -> str:
        """Generate Tello state string with all telemetry data"""
        # Format: mid:x;y;z;mpry:pitch;roll;yaw;vgx;vgy;vgz;templ;temph;tof;h;bat;baro;time;agx;agy;agz;
        
        # Mission pad data
        mid = drone_state.mission_pad_id if drone_state.mission_pad_id != -1 else -2
        x = drone_state.mission_pad_x if mid != -2 else -200
        y = drone_state.mission_pad_y if mid != -2 else -200
        z = drone_state.mission_pad_z if mid != -2 else -200
        
        # Attitude (pitch, roll, yaw) - add sensor noise only for reporting
        pitch = int(drone_state.rotation.x + random.uniform(-self.rotation_noise, self.rotation_noise))
        roll = int(drone_state.rotation.y + random.uniform(-self.rotation_noise, self.rotation_noise))
        yaw = int(drone_state.rotation.z + random.uniform(-self.rotation_noise, self.rotation_noise))
        
        # Velocity - add sensor noise only for reporting
        vgx = int(drone_state.velocity.x + random.uniform(-self.velocity_noise, self.velocity_noise))
        vgy = int(drone_state.velocity.y + random.uniform(-self.velocity_noise, self.velocity_noise))
        vgz = int(drone_state.velocity.z + random.uniform(-self.velocity_noise, self.velocity_noise))
        
        # Temperature (low and high - simulate dual sensors)
        templ = drone_state.temperature
        temph = drone_state.temperature + random.randint(-2, 2)
        
        # Time of flight sensor (distance to ground) - add sensor noise
        tof_base = max(30, int(drone_state.position.z))
        tof = max(30, tof_base + random.randint(-3, 3))  # Minimum 30cm reading with noise
        
        # Height (barometer)
        h = drone_state.barometer
        
        # Battery
        bat = drone_state.battery
        
        # Barometer (pressure altitude) - add sensor noise
        baro_base = int(drone_state.position.z * 0.83)
        baro = max(0, baro_base + random.randint(-5, 5))  # Simplified conversion with noise
        
        # Flight time
        flight_time = drone_state.flight_time
        
        # Acceleration (already has noise added in _add_sensor_noise)
        agx = int(drone_state.acceleration.x)
        agy = int(drone_state.acceleration.y)
        agz = int(drone_state.acceleration.z)
        
        # Build state string
        state_string = (
            f"mid:{mid};x:{x};y:{y};z:{z};"
            f"mpry:{pitch};{roll};{yaw};"
            f"vgx:{vgx};vgy:{vgy};vgz:{vgz};"
            f"templ:{templ};temph:{temph};"
            f"tof:{tof};h:{h};bat:{bat};baro:{baro};"
            f"time:{flight_time};"
            f"agx:{agx};agy:{agy};agz:{agz};"
        )
        
        return state_string
    
    def simulate_sensor_failure(self, drone_state: DroneState, sensor_type: str) -> None:
        """Simulate sensor failures for testing"""
        if sensor_type == "battery":
            drone_state.battery = 0
        elif sensor_type == "temperature":
            drone_state.temperature = -1  # Invalid reading
        elif sensor_type == "barometer":
            drone_state.barometer = -1
        elif sensor_type == "mission_pad":
            drone_state.mission_pad_id = -1
        elif sensor_type == "acceleration":
            drone_state.acceleration = Vector3(0, 0, 0)
    
    def add_mission_pad(self, pad_id: int, position: Vector3) -> None:
        """Add a custom mission pad to the simulation"""
        self.mission_pads[pad_id] = position
    
    def remove_mission_pad(self, pad_id: int) -> None:
        """Remove a mission pad from the simulation"""
        if pad_id in self.mission_pads:
            del self.mission_pads[pad_id]
    
    def get_mission_pad_positions(self) -> dict:
        """Get all mission pad positions"""
        return self.mission_pads.copy()
    
    def set_detection_range(self, range_cm: int) -> None:
        """Set mission pad detection range"""
        self.mission_pad_detection_range = max(50, min(500, range_cm))
    
    def reset_battery(self, drone_state: DroneState, level: int = 100) -> None:
        """Reset battery to specified level"""
        drone_state.battery = max(0, min(100, level))
        self.battery_start_time = time.time()