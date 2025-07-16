"""
Core data models for the RoboMaster TT 3D Simulator
"""
from dataclasses import dataclass
from typing import Tuple, List
from datetime import datetime


@dataclass
class Vector3:
    """3D vector for position, velocity, rotation, etc."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)


@dataclass
class DroneState:
    """Complete state representation of a simulated drone"""
    # Identity
    drone_id: str
    udp_port: int
    
    # Position and Orientation
    position: Vector3 = None  # x, y, z in cm
    rotation: Vector3 = None  # pitch, yaw, roll in degrees
    velocity: Vector3 = None  # vx, vy, vz in cm/s
    
    # Flight Status
    is_flying: bool = False
    is_connected: bool = True
    flight_time: int = 0  # seconds
    
    # Telemetry
    battery: int = 100  # percentage 0-100
    temperature: int = 25  # celsius
    barometer: int = 0  # cm
    acceleration: Vector3 = None  # agx, agy, agz in cm/s²
    
    # Mission Pad Detection
    mission_pad_id: int = -1  # -1 if not detected
    mission_pad_x: int = -100
    mission_pad_y: int = -100
    mission_pad_z: int = -100
    
    # Settings
    speed: int = 100  # cm/s
    rc_values: Tuple[int, int, int, int] = (0, 0, 0, 0)  # a, b, c, d
    
    # Timestamps
    last_command_time: float = 0.0
    last_update_time: float = 0.0
    
    def __post_init__(self):
        """Initialize default values for Vector3 fields"""
        if self.position is None:
            self.position = Vector3()
        if self.rotation is None:
            self.rotation = Vector3()
        if self.velocity is None:
            self.velocity = Vector3()
        if self.acceleration is None:
            self.acceleration = Vector3()
        
        # Set initial timestamps
        current_time = datetime.now().timestamp()
        if self.last_command_time == 0.0:
            self.last_command_time = current_time
        if self.last_update_time == 0.0:
            self.last_update_time = current_time


@dataclass
class DroneCommand:
    """Represents a command sent to a drone"""
    command_type: str  # "control", "setting", "read"
    command: str
    parameters: List[str]
    timestamp: float
    response_expected: bool = True
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class SimulationConfig:
    """Configuration settings for the simulation environment"""
    # Server Settings
    backend_port: int = 8000
    websocket_port: int = 8001
    
    # Drone Settings
    max_drones: int = 10
    base_udp_port: int = 8889
    default_speed: int = 100  # cm/s
    
    # Physics Settings
    gravity: float = 9.81
    air_resistance: float = 0.1
    max_acceleration: float = 500  # cm/s²
    
    # Simulation Settings
    update_rate: int = 30  # Hz
    battery_drain_rate: float = 0.1  # %/minute
    
    # 3D Scene Settings
    scene_bounds: Tuple[int, int, int] = (1000, 1000, 500)  # x, y, z in cm