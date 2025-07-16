"""
Mock Drone Client - Simulates RoboMaster TT drone UDP server
"""
import asyncio
import socket
import logging
from typing import Optional, Callable
from datetime import datetime
import time
import sys
import os
import aiohttp
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import DroneState, DroneCommand, SimulationConfig, Vector3
from .physics_engine import PhysicsEngine
from .telemetry_simulator import TelemetrySimulator


class MockDrone:
    """Main mock drone class that simulates a RoboMaster TT drone"""
    
    def __init__(self, drone_id: str, udp_port: int, backend_url: str = "http://localhost:8000", config: Optional[SimulationConfig] = None):
        self.drone_id = drone_id
        self.udp_port = udp_port
        self.backend_url = backend_url
        
        # Initialize configuration
        self.config = config or SimulationConfig()
        
        # Initialize drone state
        self.state = DroneState(
            drone_id=drone_id,
            udp_port=udp_port
        )
        
        # Initialize physics engine
        self.physics_engine = PhysicsEngine(self.config)
        
        # Initialize telemetry simulator
        self.telemetry_simulator = TelemetrySimulator(self.config)
        
        # Backend communication
        self.http_session = None
        self.backend_update_task = None
        self.last_backend_update = time.time()
        self.backend_update_interval = 1.0 / 10.0  # 10 Hz backend updates
        
        # Physics update task
        self.physics_task = None
        self.last_physics_update = time.time()
        
        # UDP server components
        self.socket = None
        self.running = False
        self.server_task = None
        
        # Command processing
        self.command_handlers = {}
        self.setup_command_handlers()
        
        # Logging
        self.logger = logging.getLogger(f"MockDrone-{drone_id}")
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging for the mock drone"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - MockDrone-{self.drone_id} - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def setup_command_handlers(self):
        """Initialize all RoboMaster TT command handlers"""
        self.command_handlers = {
            # Control Commands
            'command': self.handle_command_mode,
            'takeoff': self.handle_takeoff,
            'land': self.handle_land,
            'emergency': self.handle_emergency,
            'up': self.handle_up,
            'down': self.handle_down,
            'left': self.handle_left,
            'right': self.handle_right,
            'forward': self.handle_forward,
            'back': self.handle_back,
            'cw': self.handle_cw,
            'ccw': self.handle_ccw,
            'stop': self.handle_stop,
            'flip': self.handle_flip,
            'go': self.handle_go,
            'curve': self.handle_curve,
            'motoron': self.handle_motoron,
            'motoroff': self.handle_motoroff,
            'throwfly': self.handle_throwfly,
            
            # Setting Commands
            'speed': self.handle_speed_setting,
            'rc': self.handle_rc_setting,
            'wifi': self.handle_wifi_setting,
            'mon': self.handle_mon,
            'moff': self.handle_moff,
            'mdirection': self.handle_mdirection,
            
            # Read Commands
            'speed?': self.handle_speed_query,
            'battery?': self.handle_battery_query,
            'time?': self.handle_time_query,
            'wifi?': self.handle_wifi_query,
            'sdk?': self.handle_sdk_query,
            'sn?': self.handle_sn_query,
            'hardware?': self.handle_hardware_query,
            'wifiversion?': self.handle_wifiversion_query,
            'ap?': self.handle_ap_query,
            'ssid?': self.handle_ssid_query,
            'tof?': self.handle_tof_query,
            'height?': self.handle_height_query,
            'temp?': self.handle_temp_query,
            'attitude?': self.handle_attitude_query,
            'baro?': self.handle_baro_query,
            'acceleration?': self.handle_acceleration_query,
        }
    
    async def start_udp_server(self):
        """Start the UDP server to listen for commands"""
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.udp_port))
            self.socket.setblocking(False)
            
            self.running = True
            self.logger.info(f"UDP server started on port {self.udp_port}")
            
            # Initialize HTTP session for backend communication
            self.http_session = aiohttp.ClientSession()
            
            # Start physics update loop
            self.physics_task = asyncio.create_task(self.physics_loop())
            
            # Start backend update loop
            self.backend_update_task = asyncio.create_task(self.backend_update_loop())
            
            # Start state broadcasting loop
            self.state_broadcast_task = asyncio.create_task(self.broadcast_state_packets())
            
            # Start server loop
            self.server_task = asyncio.create_task(self.server_loop())
            await asyncio.gather(self.server_task, self.physics_task, self.backend_update_task, self.state_broadcast_task)
            
        except Exception as e:
            self.logger.error(f"Failed to start UDP server: {e}")
            raise
    
    async def server_loop(self):
        """Main server loop to handle incoming UDP commands"""
        while self.running:
            try:
                # Wait for incoming data
                data, addr = await asyncio.get_event_loop().sock_recvfrom(self.socket, 1024)
                
                # Decode command
                command_str = data.decode('utf-8').strip()
                
                # Check if this is telemetry data before logging to reduce noise
                if self.is_telemetry_data(command_str):
                    continue  # Skip telemetry data completely
                
                self.logger.info(f"Received command from {addr}: {command_str}")
                
                # Process command
                response = await self.process_command(command_str)
                
                # Send response
                if response:
                    await asyncio.get_event_loop().sock_sendto(
                        self.socket, 
                        response.encode('utf-8'), 
                        addr
                    )
                    self.logger.info(f"Sent response to {addr}: {response}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in server loop: {e}")
                await asyncio.sleep(0.1)
    
    async def physics_loop(self):
        """Physics update loop for realistic drone simulation"""
        while self.running:
            try:
                current_time = time.time()
                dt = current_time - self.last_physics_update
                
                # Update physics at configured rate
                if dt >= 1.0 / self.config.update_rate:
                    # Update physics simulation
                    self.physics_engine.update_drone_physics(self.state, dt)
                    
                    # Update telemetry data
                    self.telemetry_simulator.update_telemetry(self.state, dt)
                    
                    # Update flight time if flying
                    if self.state.is_flying:
                        self.state.flight_time += int(dt)
                    
                    self.last_physics_update = current_time
                
                # Sleep for a short time to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in physics loop: {e}")
                await asyncio.sleep(0.1)
    
    async def process_command(self, command_str: str) -> str:
        """Process incoming command and return response"""
        try:
            # Check if this is telemetry data being sent back to us (ignore it)
            if self.is_telemetry_data(command_str):
                # Silently ignore telemetry data - don't log it to reduce noise
                return None  # Don't respond to telemetry data
            
            # Parse command
            command_parts = command_str.split()
            if not command_parts:
                return "error"
            
            command_name = command_parts[0].lower()
            parameters = command_parts[1:] if len(command_parts) > 1 else []
            
            # Create command object
            command = DroneCommand(
                command_type=self.get_command_type(command_name),
                command=command_name,
                parameters=parameters,
                timestamp=datetime.now().timestamp()
            )
            
            # Update last command time
            self.state.last_command_time = command.timestamp
            
            # Find and execute handler
            if command_name in self.command_handlers:
                response = await self.command_handlers[command_name](command)
            else:
                response = self.handle_unknown_command(command)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing command '{command_str}': {e}")
            return "error"
    
    def is_telemetry_data(self, command_str: str) -> bool:
        """Check if the received data is telemetry data (not a command)"""
        # Telemetry data contains semicolon-separated key:value pairs
        # and typically includes fields like pitch, roll, yaw, etc.
        if ';' in command_str and ':' in command_str:
            # Check for common telemetry fields
            telemetry_fields = ['pitch:', 'roll:', 'yaw:', 'vgx:', 'vgy:', 'vgz:', 
                              'templ:', 'temph:', 'tof:', 'h:', 'bat:', 'baro:', 
                              'time:', 'agx:', 'agy:', 'agz:']
            
            # If it contains multiple telemetry fields, it's likely telemetry data
            field_count = sum(1 for field in telemetry_fields if field in command_str)
            return field_count >= 3  # At least 3 telemetry fields
        
        return False
    
    def get_command_type(self, command_name: str) -> str:
        """Determine command type based on command name"""
        if command_name.endswith('?'):
            return "read"
        elif command_name in ['speed', 'rc', 'wifi']:
            return "setting"
        else:
            return "control"
    
    def validate_command_parameters(self, command: DroneCommand, expected_count: int) -> bool:
        """Validate command has expected number of parameters"""
        if len(command.parameters) != expected_count:
            self.logger.warning(
                f"Command '{command.command}' expects {expected_count} parameters, "
                f"got {len(command.parameters)}"
            )
            return False
        return True
    
    # Control Command Handlers
    async def handle_command_mode(self, command: DroneCommand) -> str:
        """Handle 'command' - enter SDK mode"""
        self.state.is_connected = True
        self.logger.info("Entered SDK command mode")
        return "ok"
    
    async def handle_takeoff(self, command: DroneCommand) -> str:
        """Handle 'takeoff' command"""
        if self.state.is_flying:
            return "error"
        
        # Start realistic takeoff animation
        self.physics_engine.start_takeoff_animation(self.state)
        self.logger.info("Drone taking off")
        return "ok"
    
    async def handle_land(self, command: DroneCommand) -> str:
        """Handle 'land' command"""
        # Allow landing if drone is flying OR if it's above ground (more forgiving)
        if not self.state.is_flying and self.state.position.z <= 0:
            return "error"
        
        # Start realistic landing animation
        self.physics_engine.start_landing_animation(self.state)
        self.logger.info("Drone landing")
        return "ok"
    
    async def handle_emergency(self, command: DroneCommand) -> str:
        """Handle 'emergency' command"""
        self.state.is_flying = False
        self.state.position.z = 0
        self.state.velocity = self.state.velocity.__class__()
        self.logger.warning("Emergency stop activated")
        return "ok"
    
    async def handle_up(self, command: DroneCommand) -> str:
        """Handle 'up x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                target_position = Vector3(
                    self.state.position.x,
                    self.state.position.y,
                    self.state.position.z + distance
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving up {distance}cm")
            else:
                self.logger.warning(f"Cannot move up - drone is not flying (is_flying={self.state.is_flying})")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_down(self, command: DroneCommand) -> str:
        """Handle 'down x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                target_position = Vector3(
                    self.state.position.x,
                    self.state.position.y,
                    max(0, self.state.position.z - distance)
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving down {distance}cm")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_left(self, command: DroneCommand) -> str:
        """Handle 'left x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                target_position = Vector3(
                    self.state.position.x - distance,
                    self.state.position.y,
                    self.state.position.z
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving left {distance}cm")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_right(self, command: DroneCommand) -> str:
        """Handle 'right x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                target_position = Vector3(
                    self.state.position.x + distance,
                    self.state.position.y,
                    self.state.position.z
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving right {distance}cm")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_forward(self, command: DroneCommand) -> str:
        """Handle 'forward x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                # Calculate forward direction based on drone's current yaw rotation
                import math
                yaw_radians = math.radians(self.state.rotation.z)
                
                # Forward direction in drone's local coordinate system
                # Yaw 0° = +Y (north), 90° = +X (east), 180° = -Y (south), 270° = -X (west)
                forward_x = distance * math.sin(yaw_radians)
                forward_y = distance * math.cos(yaw_radians)
                
                target_position = Vector3(
                    self.state.position.x + forward_x,
                    self.state.position.y + forward_y,
                    self.state.position.z
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving forward {distance}cm (heading {self.state.rotation.z:.1f}°)")
            else:
                self.logger.warning(f"Cannot move forward - drone is not flying (is_flying={self.state.is_flying})")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_back(self, command: DroneCommand) -> str:
        """Handle 'back x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            distance = int(command.parameters[0])
            if not (20 <= distance <= 500):
                return "error"
            
            if self.state.is_flying:
                # Calculate backward direction based on drone's current yaw rotation
                import math
                yaw_radians = math.radians(self.state.rotation.z)
                
                # Backward direction is opposite to forward
                # Forward: Yaw 0° = +Y, 90° = +X, 180° = -Y, 270° = -X
                # Backward: Yaw 0° = -Y, 90° = -X, 180° = +Y, 270° = +X
                back_x = -distance * math.sin(yaw_radians)
                back_y = -distance * math.cos(yaw_radians)
                
                target_position = Vector3(
                    self.state.position.x + back_x,
                    self.state.position.y + back_y,
                    self.state.position.z
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, self.state.speed
                )
                self.logger.info(f"Moving back {distance}cm (heading {self.state.rotation.z:.1f}°)")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_cw(self, command: DroneCommand) -> str:
        """Handle 'cw x' command - rotate clockwise"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            degrees = int(command.parameters[0])
            if not (1 <= degrees <= 360):
                return "error"
            
            target_yaw = (self.state.rotation.z + degrees) % 360
            self.physics_engine.start_rotation_animation(self.state, target_yaw)
            self.logger.info(f"Rotating clockwise {degrees} degrees")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_ccw(self, command: DroneCommand) -> str:
        """Handle 'ccw x' command - rotate counter-clockwise"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            degrees = int(command.parameters[0])
            if not (1 <= degrees <= 360):
                return "error"
            
            target_yaw = (self.state.rotation.z - degrees) % 360
            self.physics_engine.start_rotation_animation(self.state, target_yaw)
            self.logger.info(f"Rotating counter-clockwise {degrees} degrees")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_stop(self, command: DroneCommand) -> str:
        """Handle 'stop' command"""
        self.state.velocity = self.state.velocity.__class__()  # Reset velocity
        self.logger.info("Stopping movement")
        return "ok"
    
    async def handle_flip(self, command: DroneCommand) -> str:
        """Handle 'flip x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        direction = command.parameters[0].lower()
        if direction not in ['l', 'r', 'f', 'b']:
            return "error"
        
        if not self.state.is_flying:
            return "error"
        
        # Start realistic flip animation
        self.physics_engine.start_flip_animation(self.state, direction)
        self.logger.info(f"Performing flip in direction: {direction}")
        return "ok"
    
    async def handle_go(self, command: DroneCommand) -> str:
        """Handle 'go x y z speed' command"""
        if not self.validate_command_parameters(command, 4):
            return "error"
        
        try:
            x, y, z, speed = map(int, command.parameters)
            
            # Validate ranges
            if not (-500 <= x <= 500) or not (-500 <= y <= 500) or not (-500 <= z <= 500):
                return "error"
            if not (10 <= speed <= 100):
                return "error"
            
            if self.state.is_flying:
                target_position = Vector3(
                    self.state.position.x + x,
                    self.state.position.y + y,
                    max(0, self.state.position.z + z)
                )
                self.physics_engine.start_movement_animation(
                    self.state, target_position, speed
                )
                self.logger.info(f"Moving to relative position ({x}, {y}, {z}) at speed {speed}")
            
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_curve(self, command: DroneCommand) -> str:
        """Handle 'curve x1 y1 z1 x2 y2 z2 speed' command"""
        if not self.validate_command_parameters(command, 7):
            return "error"
        
        try:
            x1, y1, z1, x2, y2, z2, speed = map(int, command.parameters)
            
            # Validate ranges
            if not all(-500 <= coord <= 500 for coord in [x1, y1, z1, x2, y2, z2]):
                return "error"
            if not (10 <= speed <= 60):
                return "error"
            
            if self.state.is_flying:
                # Create control points for Bezier curve
                control_point1 = Vector3(
                    self.state.position.x + x1,
                    self.state.position.y + y1,
                    max(0, self.state.position.z + z1)
                )
                target_position = Vector3(
                    self.state.position.x + x2,
                    self.state.position.y + y2,
                    max(0, self.state.position.z + z2)
                )
                
                # Start curve animation with control points
                self.physics_engine.start_movement_animation(
                    self.state, target_position, speed, 'curve'
                )
                
                # Add control points to animation
                if self.drone_id in self.physics_engine.animations:
                    self.physics_engine.animations[self.drone_id]['control_point1'] = control_point1
                    self.physics_engine.animations[self.drone_id]['control_point2'] = target_position
                
                self.logger.info(f"Flying curve to ({x2}, {y2}, {z2}) via ({x1}, {y1}, {z1})")
            
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_motoron(self, command: DroneCommand) -> str:
        """Handle 'motoron' command"""
        self.logger.info("Motor-On mode enabled")
        return "ok"
    
    async def handle_motoroff(self, command: DroneCommand) -> str:
        """Handle 'motoroff' command"""
        self.logger.info("Motor-On mode disabled")
        return "ok"
    
    async def handle_throwfly(self, command: DroneCommand) -> str:
        """Handle 'throwfly' command"""
        if not self.state.is_flying:
            self.state.is_flying = True
            self.state.position.z = 100
            self.logger.info("Throw and fly activated")
        return "ok"
    
    # Setting Command Handlers
    async def handle_speed_setting(self, command: DroneCommand) -> str:
        """Handle 'speed x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            speed = int(command.parameters[0])
            if not (10 <= speed <= 100):
                return "error"
            
            self.state.speed = speed
            self.logger.info(f"Speed set to {speed} cm/s")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_rc_setting(self, command: DroneCommand) -> str:
        """Handle 'rc a b c d' command"""
        if not self.validate_command_parameters(command, 4):
            return "error"
        
        try:
            a, b, c, d = map(int, command.parameters)
            
            # Validate ranges
            if not all(-100 <= val <= 100 for val in [a, b, c, d]):
                return "error"
            
            self.state.rc_values = (a, b, c, d)
            self.logger.info(f"RC values set to ({a}, {b}, {c}, {d})")
            return "ok"
        except ValueError:
            return "error"
    
    async def handle_wifi_setting(self, command: DroneCommand) -> str:
        """Handle 'wifi ssid pass' command"""
        if not self.validate_command_parameters(command, 2):
            return "error"
        
        ssid, password = command.parameters
        self.logger.info(f"WiFi configured: SSID={ssid}")
        return "ok"
    
    async def handle_mon(self, command: DroneCommand) -> str:
        """Handle 'mon' command - enable mission pad detection"""
        self.logger.info("Mission pad detection enabled")
        return "ok"
    
    async def handle_moff(self, command: DroneCommand) -> str:
        """Handle 'moff' command - disable mission pad detection"""
        self.state.mission_pad_id = -1
        self.logger.info("Mission pad detection disabled")
        return "ok"
    
    async def handle_mdirection(self, command: DroneCommand) -> str:
        """Handle 'mdirection x' command"""
        if not self.validate_command_parameters(command, 1):
            return "error"
        
        try:
            direction = int(command.parameters[0])
            if direction not in [0, 1, 2]:
                return "error"
            
            self.logger.info(f"Mission pad detection direction set to {direction}")
            return "ok"
        except ValueError:
            return "error"
    
    # Read Command Handlers
    async def handle_speed_query(self, command: DroneCommand) -> str:
        """Handle 'speed?' query"""
        return f"x:{int(self.state.velocity.x)} y:{int(self.state.velocity.y)} z:{int(self.state.velocity.z)}"
    
    async def handle_battery_query(self, command: DroneCommand) -> str:
        """Handle 'battery?' query"""
        return str(self.state.battery)
    
    async def handle_time_query(self, command: DroneCommand) -> str:
        """Handle 'time?' query"""
        return str(self.state.flight_time)
    
    async def handle_wifi_query(self, command: DroneCommand) -> str:
        """Handle 'wifi?' query"""
        return "90"  # Signal strength
    
    async def handle_sdk_query(self, command: DroneCommand) -> str:
        """Handle 'sdk?' query"""
        return "ok"
    
    async def handle_sn_query(self, command: DroneCommand) -> str:
        """Handle 'sn?' query"""
        return f"0TQZH77ED00{self.drone_id[-1]}"  # Mock serial number
    
    async def handle_hardware_query(self, command: DroneCommand) -> str:
        """Handle 'hardware?' query"""
        return "RMTT"
    
    async def handle_wifiversion_query(self, command: DroneCommand) -> str:
        """Handle 'wifiversion?' query"""
        return "1.3.0.0"
    
    async def handle_ap_query(self, command: DroneCommand) -> str:
        """Handle 'ap?' query"""
        return "TELLO-ED00A1"  # Mock AP name
    
    async def handle_ssid_query(self, command: DroneCommand) -> str:
        """Handle 'ssid?' query"""
        return "TELLO-ED00A1"  # Mock SSID
    
    async def handle_tof_query(self, command: DroneCommand) -> str:
        """Handle 'tof?' query - Time of Flight sensor (distance to ground)"""
        return str(max(30, int(self.state.position.z)))
    
    async def handle_height_query(self, command: DroneCommand) -> str:
        """Handle 'height?' query - Barometer height"""
        return str(self.state.barometer)
    
    async def handle_temp_query(self, command: DroneCommand) -> str:
        """Handle 'temp?' query - Temperature"""
        return str(self.state.temperature)
    
    async def handle_attitude_query(self, command: DroneCommand) -> str:
        """Handle 'attitude?' query - Pitch, roll, yaw"""
        return f"pitch:{int(self.state.rotation.x)};roll:{int(self.state.rotation.y)};yaw:{int(self.state.rotation.z)};"
    
    async def handle_baro_query(self, command: DroneCommand) -> str:
        """Handle 'baro?' query - Barometer reading"""
        return str(self.state.barometer)
    
    async def handle_acceleration_query(self, command: DroneCommand) -> str:
        """Handle 'acceleration?' query - Accelerometer readings"""
        return f"agx:{int(self.state.acceleration.x)};agy:{int(self.state.acceleration.y)};agz:{int(self.state.acceleration.z)};"
    
    def handle_unknown_command(self, command: DroneCommand) -> str:
        """Handle unknown commands"""
        self.logger.warning(f"Unknown command: {command.command}")
        return "error"
    
    async def backend_update_loop(self):
        """Backend update loop to send drone state to backend server"""
        while self.running:
            try:
                current_time = time.time()
                dt = current_time - self.last_backend_update
                
                # Send updates at configured rate
                if dt >= self.backend_update_interval:
                    await self.send_state_to_backend()
                    self.last_backend_update = current_time
                
                # Sleep for a short time to prevent busy waiting
                await asyncio.sleep(0.05)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in backend update loop: {e}")
                await asyncio.sleep(1.0)  # Wait longer on error
    
    async def send_state_to_backend(self):
        """Send current drone state to backend server"""
        if not self.http_session:
            return
        
        try:
            # Prepare state data for backend
            state_data = {
                "udp_port": self.state.udp_port,
                "position": {
                    "x": self.state.position.x,
                    "y": self.state.position.y,
                    "z": self.state.position.z
                },
                "rotation": {
                    "x": self.state.rotation.x,
                    "y": self.state.rotation.y,
                    "z": self.state.rotation.z
                },
                "velocity": {
                    "x": self.state.velocity.x,
                    "y": self.state.velocity.y,
                    "z": self.state.velocity.z
                },
                "acceleration": {
                    "x": self.state.acceleration.x,
                    "y": self.state.acceleration.y,
                    "z": self.state.acceleration.z
                },
                "is_flying": self.state.is_flying,
                "is_connected": self.state.is_connected,
                "flight_time": self.state.flight_time,
                "battery": self.state.battery,
                "temperature": self.state.temperature,
                "barometer": self.state.barometer,
                "mission_pad_id": self.state.mission_pad_id,
                "mission_pad_x": self.state.mission_pad_x,
                "mission_pad_y": self.state.mission_pad_y,
                "mission_pad_z": self.state.mission_pad_z,
                "speed": self.state.speed,
                "rc_values": self.state.rc_values,
                "last_command_time": self.state.last_command_time,
                "last_update_time": self.state.last_update_time
            }
            
            # Send POST request to backend
            url = f"{self.backend_url}/api/drones/{self.drone_id}/state"
            async with self.http_session.post(url, json=state_data) as response:
                if response.status != 200:
                    self.logger.warning(f"Backend update failed: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Error sending state to backend: {e}")

    def format_state_packet(self) -> str:
        """Format current state as Tello SDK state packet string"""
        # Format state packet according to Tello SDK specification
        state_parts = [
            f"pitch:{int(self.state.rotation.x)}",
            f"roll:{int(self.state.rotation.y)}",
            f"yaw:{int(self.state.rotation.z)}",
            f"vgx:{int(self.state.velocity.x)}",
            f"vgy:{int(self.state.velocity.y)}",
            f"vgz:{int(self.state.velocity.z)}",
            f"templ:{int(self.state.temperature)}",
            f"temph:{int(self.state.temperature + 2)}",
            f"tof:{max(30, int(self.state.position.z))}",
            f"h:{int(self.state.position.z)}",
            f"bat:{self.state.battery}",
            f"baro:{self.state.barometer:.2f}",
            f"time:{self.state.flight_time}",
            f"agx:{int(self.state.acceleration.x)}",
            f"agy:{int(self.state.acceleration.y)}",
            f"agz:{int(self.state.acceleration.z)}"
        ]
        
        # Add mission pad info if available
        if self.state.mission_pad_id >= 0:
            state_parts.extend([
                f"mid:{self.state.mission_pad_id}",
                f"x:{int(self.state.mission_pad_x)}",
                f"y:{int(self.state.mission_pad_y)}",
                f"z:{int(self.state.mission_pad_z)}"
            ])
        
        return ";".join(state_parts) + ";"

    async def broadcast_state_packets(self):
        """Broadcast state packets on UDP port 8890 for djitellopy compatibility"""
        state_socket = None
        try:
            # Create UDP socket for broadcasting state
            state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            state_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.logger.info("Started broadcasting state packets on port 8890")
            
            while self.running:
                try:
                    # Format state packet
                    state_packet = self.format_state_packet()
                    
                    # Broadcast to all connected clients (broadcast to local network)
                    state_socket.sendto(
                        state_packet.encode('utf-8'),
                        ('255.255.255.255', 8890)
                    )
                    
                    # Also send to localhost for local testing
                    state_socket.sendto(
                        state_packet.encode('utf-8'),
                        ('127.0.0.1', 8890)
                    )
                    
                    # Send at 10Hz (every 100ms)
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error broadcasting state packet: {e}")
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.logger.error(f"Failed to setup state broadcasting: {e}")
        finally:
            if state_socket:
                state_socket.close()
    
    async def stop(self):
        """Stop the mock drone and cleanup resources"""
        self.running = False
        
        # Cancel tasks
        if self.server_task:
            self.server_task.cancel()
        if self.physics_task:
            self.physics_task.cancel()
        if self.backend_update_task:
            self.backend_update_task.cancel()
        if hasattr(self, 'state_broadcast_task') and self.state_broadcast_task:
            self.state_broadcast_task.cancel()
        if self.backend_update_task:
            self.backend_update_task.cancel()
        
        # Close socket
        if self.socket:
            self.socket.close()
        
        # Close HTTP session
        if self.http_session:
            await self.http_session.close()
        
        self.logger.info(f"Mock drone {self.drone_id} stopped")


async def main():
    """Main function for testing the mock drone"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RoboMaster TT Mock Drone')
    parser.add_argument('--drone-id', default='drone_1', help='Drone identifier')
    parser.add_argument('--port', type=int, default=8889, help='UDP port to listen on')
    parser.add_argument('--backend', default='http://localhost:8000', help='Backend server URL')
    
    args = parser.parse_args()
    
    # Create and start mock drone
    drone = MockDrone(args.drone_id, args.port, args.backend)
    
    try:
        await drone.start_udp_server()
    except KeyboardInterrupt:
        print("\nShutting down mock drone...")
        await drone.stop()


if __name__ == "__main__":
    asyncio.run(main())