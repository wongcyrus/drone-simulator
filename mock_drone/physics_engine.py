"""
Physics simulation engine for realistic drone movement and behavior
"""
import math
import time
from typing import Tuple, Optional
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import DroneState, Vector3, SimulationConfig


class PhysicsEngine:
    """Handles realistic physics simulation for drone movement"""
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.last_update_time = time.time()
        
        # Physics constants
        self.gravity = config.gravity  # m/s²
        self.air_resistance = config.air_resistance
        self.max_acceleration = config.max_acceleration  # cm/s²
        
        # Movement parameters
        self.takeoff_speed = 50  # cm/s
        self.landing_speed = 30  # cm/s
        self.hover_height = 100  # cm
        self.max_tilt_angle = 30  # degrees
        
        # Animation states
        self.animations = {}  # drone_id -> animation_state
    
    def update_drone_physics(self, drone_state: DroneState, dt: float) -> None:
        """Update drone physics for one time step"""
        drone_id = drone_state.drone_id
        
        # Handle active animations
        if drone_id in self.animations:
            self._update_animation(drone_state, dt)
        
        # Apply physics forces
        self._apply_gravity(drone_state, dt)
        self._apply_air_resistance(drone_state, dt)
        self._apply_boundary_constraints(drone_state)
        
        # Update position based on velocity
        drone_state.position.x += drone_state.velocity.x * dt
        drone_state.position.y += drone_state.velocity.y * dt
        drone_state.position.z += drone_state.velocity.z * dt
        
        # Ensure drone doesn't go below ground
        if drone_state.position.z < 0:
            drone_state.position.z = 0
            drone_state.velocity.z = 0
            # Only set is_flying to False if we're actually landing (not just at ground level)
            if drone_state.is_flying and drone_state.drone_id in self.animations:
                animation = self.animations[drone_state.drone_id]
                if animation.get('type') == 'landing':
                    drone_state.is_flying = False
        
        # Don't auto-land drone just because it's at ground level during other animations
        # The drone should only land when explicitly commanded or when landing animation completes
        
        # Update timestamps
        drone_state.last_update_time = time.time()
    
    def start_takeoff_animation(self, drone_state: DroneState) -> None:
        """Start takeoff animation"""
        if drone_state.is_flying:
            return
        
        self.animations[drone_state.drone_id] = {
            'type': 'takeoff',
            'start_time': time.time(),
            'start_position': Vector3(
                drone_state.position.x,
                drone_state.position.y,
                drone_state.position.z
            ),
            'target_height': self.hover_height,
            'duration': max(self.hover_height / self.takeoff_speed, 0.1)
        }
        
        drone_state.is_flying = True
    
    def start_landing_animation(self, drone_state: DroneState) -> None:
        """Start landing animation"""
        if not drone_state.is_flying:
            return
        
        self.animations[drone_state.drone_id] = {
            'type': 'landing',
            'start_time': time.time(),
            'start_position': Vector3(
                drone_state.position.x,
                drone_state.position.y,
                drone_state.position.z
            ),
            'target_height': 0,
            'duration': max(drone_state.position.z / self.landing_speed, 0.1)
        }
    
    def start_movement_animation(self, drone_state: DroneState, target_position: Vector3, 
                               speed: float, animation_type: str = 'linear') -> None:
        """Start movement animation to target position"""
        if not drone_state.is_flying:
            return
        
        # Calculate distance and duration
        distance = self._calculate_distance(drone_state.position, target_position)
        duration = distance / speed if speed > 0 else 1.0
        
        self.animations[drone_state.drone_id] = {
            'type': animation_type,
            'start_time': time.time(),
            'start_position': Vector3(
                drone_state.position.x,
                drone_state.position.y,
                drone_state.position.z
            ),
            'target_position': target_position,
            'duration': duration,
            'speed': speed
        }
    
    def start_flip_animation(self, drone_state: DroneState, direction: str) -> None:
        """Start flip animation"""
        if not drone_state.is_flying:
            return
        
        # Flip directions: l=left, r=right, f=forward, b=back
        rotation_axis = {
            'l': 'y',  # Roll left
            'r': 'y',  # Roll right
            'f': 'x',  # Pitch forward
            'b': 'x'   # Pitch backward
        }
        
        rotation_amount = 360 if direction in ['l', 'f'] else -360
        
        self.animations[drone_state.drone_id] = {
            'type': 'flip',
            'start_time': time.time(),
            'start_rotation': Vector3(
                drone_state.rotation.x,
                drone_state.rotation.y,
                drone_state.rotation.z
            ),
            'axis': rotation_axis.get(direction, 'y'),
            'rotation_amount': rotation_amount,
            'duration': 1.0  # 1 second flip
        }
    
    def start_rotation_animation(self, drone_state: DroneState, target_yaw: float) -> None:
        """Start rotation animation"""
        # Only allow rotation if drone is flying
        if not drone_state.is_flying:
            return
            
        self.animations[drone_state.drone_id] = {
            'type': 'rotation',
            'start_time': time.time(),
            'start_yaw': drone_state.rotation.z,
            'target_yaw': target_yaw,
            'duration': max(abs(target_yaw - drone_state.rotation.z) / 90.0, 0.1),  # 90 deg/sec, min 0.1s
            'hover_height': max(drone_state.position.z, self.hover_height)  # Preserve current altitude
        }
    
    def _update_animation(self, drone_state: DroneState, dt: float) -> None:
        """Update active animation for drone"""
        drone_id = drone_state.drone_id
        animation = self.animations[drone_id]
        
        current_time = time.time()
        elapsed_time = current_time - animation['start_time']
        progress = min(elapsed_time / max(animation['duration'], 0.001), 1.0)
        
        if animation['type'] == 'takeoff':
            self._update_takeoff_animation(drone_state, animation, progress)
        elif animation['type'] == 'landing':
            self._update_landing_animation(drone_state, animation, progress)
        elif animation['type'] == 'linear':
            self._update_linear_movement(drone_state, animation, progress)
        elif animation['type'] == 'curve':
            self._update_curve_movement(drone_state, animation, progress)
        elif animation['type'] == 'flip':
            self._update_flip_animation(drone_state, animation, progress)
        elif animation['type'] == 'rotation':
            self._update_rotation_animation(drone_state, animation, progress)
        
        # Remove completed animations
        if progress >= 1.0:
            self._complete_animation(drone_state, animation)
            del self.animations[drone_id]
    
    def _update_takeoff_animation(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update takeoff animation"""
        # Smooth acceleration curve
        smooth_progress = self._smooth_step(progress)
        
        start_z = animation['start_position'].z
        target_z = animation['target_height']
        
        drone_state.position.z = start_z + (target_z - start_z) * smooth_progress
        drone_state.velocity.z = self.takeoff_speed * (1 - progress)
    
    def _update_landing_animation(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update landing animation"""
        # Smooth deceleration curve
        smooth_progress = self._smooth_step(progress)
        
        start_z = animation['start_position'].z
        target_z = animation['target_height']
        
        drone_state.position.z = start_z + (target_z - start_z) * smooth_progress
        drone_state.velocity.z = -self.landing_speed * (1 - progress)
        
        if progress >= 1.0:
            drone_state.is_flying = False
            drone_state.velocity = Vector3()
    
    def _update_linear_movement(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update linear movement animation"""
        smooth_progress = self._smooth_step(progress)
        
        start_pos = animation['start_position']
        target_pos = animation['target_position']
        
        drone_state.position.x = start_pos.x + (target_pos.x - start_pos.x) * smooth_progress
        drone_state.position.y = start_pos.y + (target_pos.y - start_pos.y) * smooth_progress
        drone_state.position.z = start_pos.z + (target_pos.z - start_pos.z) * smooth_progress
        
        # Calculate velocity
        if progress < 1.0:
            remaining_distance = self._calculate_distance(drone_state.position, target_pos)
            remaining_time = animation['duration'] * (1 - progress)
            if remaining_time > 0:
                speed = remaining_distance / remaining_time
                direction = self._normalize_vector(Vector3(
                    target_pos.x - drone_state.position.x,
                    target_pos.y - drone_state.position.y,
                    target_pos.z - drone_state.position.z
                ))
                drone_state.velocity = direction * speed
    
    def _update_curve_movement(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update curve movement animation using Bezier curve"""
        # Bezier curve with control points
        p0 = animation['start_position']
        p1 = animation.get('control_point1', p0)
        p2 = animation.get('control_point2', animation['target_position'])
        p3 = animation['target_position']
        
        # Cubic Bezier interpolation
        t = self._smooth_step(progress)
        
        drone_state.position.x = self._cubic_bezier(t, p0.x, p1.x, p2.x, p3.x)
        drone_state.position.y = self._cubic_bezier(t, p0.y, p1.y, p2.y, p3.y)
        drone_state.position.z = self._cubic_bezier(t, p0.z, p1.z, p2.z, p3.z)
    
    def _update_flip_animation(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update flip animation"""
        # Use sine wave for smooth flip motion
        flip_progress = math.sin(progress * math.pi)
        
        start_rotation = animation['start_rotation']
        axis = animation['axis']
        rotation_amount = animation['rotation_amount']
        
        if axis == 'x':
            drone_state.rotation.x = start_rotation.x + rotation_amount * flip_progress
        elif axis == 'y':
            drone_state.rotation.y = start_rotation.y + rotation_amount * flip_progress
        else:  # z axis
            drone_state.rotation.z = start_rotation.z + rotation_amount * flip_progress
        
        # Add slight vertical movement during flip
        drone_state.position.z += 20 * math.sin(progress * math.pi)
    
    def _update_rotation_animation(self, drone_state: DroneState, animation: dict, progress: float) -> None:
        """Update rotation animation"""
        smooth_progress = self._smooth_step(progress)
        
        start_yaw = animation['start_yaw']
        target_yaw = animation['target_yaw']
        
        # Handle angle wrapping
        angle_diff = target_yaw - start_yaw
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        
        # Calculate current rotation
        current_yaw = (start_yaw + angle_diff * smooth_progress) % 360
        drone_state.rotation.z = current_yaw
        
        # Maintain altitude during rotation - force Z position to hover height
        hover_height = animation.get('hover_height', self.hover_height)
        drone_state.position.z = hover_height
        drone_state.velocity.z = 0  # Stop any vertical movement
    
    def _complete_animation(self, drone_state: DroneState, animation: dict) -> None:
        """Complete animation and set final state"""
        if animation['type'] == 'landing':
            drone_state.is_flying = False
            drone_state.position.z = 0
            drone_state.velocity = Vector3()
        elif animation['type'] in ['linear', 'curve']:
            drone_state.position = animation['target_position']
            drone_state.velocity = Vector3()
        elif animation['type'] == 'flip':
            # Reset rotation after flip
            start_rotation = animation['start_rotation']
            drone_state.rotation = Vector3(
                start_rotation.x,
                start_rotation.y,
                start_rotation.z
            )
    
    def _apply_gravity(self, drone_state: DroneState, dt: float) -> None:
        """Apply gravity effect"""
        if not drone_state.is_flying:
            return
        
        # Don't apply gravity during certain animations that manage their own Z position
        if drone_state.drone_id in self.animations:
            animation = self.animations[drone_state.drone_id]
            if animation['type'] in ['takeoff', 'landing', 'linear', 'curve']:
                return  # These animations control Z position directly
        
        # Convert gravity from m/s² to cm/s²
        gravity_cm = self.gravity * 100
        
        # Apply gravity to vertical velocity
        drone_state.velocity.z -= gravity_cm * dt
        
        # Add hover stabilization for rotation and flip animations, or when just hovering
        if drone_state.drone_id in self.animations:
            animation = self.animations[drone_state.drone_id]
            if animation['type'] in ['rotation', 'flip']:
                # Maintain hover height during rotation/flip
                target_height = self.hover_height
                height_error = target_height - drone_state.position.z
                
                # Apply corrective force to maintain altitude
                hover_force = height_error * 2.0  # Proportional control
                drone_state.velocity.z += hover_force * dt
        else:
            # No active animation - maintain current altitude (hover stabilization)
            if drone_state.position.z > 0:  # Only if drone is airborne
                # Use current position as target to maintain stable hover
                target_height = max(drone_state.position.z, self.hover_height)
                height_error = target_height - drone_state.position.z
                
                # Apply gentle corrective force to counteract gravity
                hover_force = height_error * 1.5 + gravity_cm  # Proportional + gravity compensation
                drone_state.velocity.z += hover_force * dt
    
    def _apply_air_resistance(self, drone_state: DroneState, dt: float) -> None:
        """Apply air resistance"""
        resistance_factor = 1.0 - (self.air_resistance * dt)
        resistance_factor = max(0.0, resistance_factor)
        
        drone_state.velocity.x *= resistance_factor
        drone_state.velocity.y *= resistance_factor
        drone_state.velocity.z *= resistance_factor
    
    def _apply_boundary_constraints(self, drone_state: DroneState) -> None:
        """Apply scene boundary constraints"""
        bounds = self.config.scene_bounds
        
        # X boundaries
        if drone_state.position.x < -bounds[0] / 2:
            drone_state.position.x = -bounds[0] / 2
            drone_state.velocity.x = 0
        elif drone_state.position.x > bounds[0] / 2:
            drone_state.position.x = bounds[0] / 2
            drone_state.velocity.x = 0
        
        # Y boundaries
        if drone_state.position.y < -bounds[1] / 2:
            drone_state.position.y = -bounds[1] / 2
            drone_state.velocity.y = 0
        elif drone_state.position.y > bounds[1] / 2:
            drone_state.position.y = bounds[1] / 2
            drone_state.velocity.y = 0
        
        # Z boundaries
        if drone_state.position.z > bounds[2]:
            drone_state.position.z = bounds[2]
            drone_state.velocity.z = 0
    
    def _calculate_distance(self, pos1: Vector3, pos2: Vector3) -> float:
        """Calculate 3D distance between two positions"""
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _normalize_vector(self, vector: Vector3) -> Vector3:
        """Normalize a vector to unit length"""
        length = math.sqrt(vector.x*vector.x + vector.y*vector.y + vector.z*vector.z)
        if length == 0:
            return Vector3()
        return Vector3(vector.x/length, vector.y/length, vector.z/length)
    
    def _smooth_step(self, t: float) -> float:
        """Smooth step function for easing"""
        return t * t * (3.0 - 2.0 * t)
    
    def _cubic_bezier(self, t: float, p0: float, p1: float, p2: float, p3: float) -> float:
        """Cubic Bezier interpolation"""
        u = 1 - t
        return (u*u*u * p0 + 3*u*u*t * p1 + 3*u*t*t * p2 + t*t*t * p3)
    
    def is_animating(self, drone_id: str) -> bool:
        """Check if drone is currently animating"""
        return drone_id in self.animations
    
    def stop_animation(self, drone_id: str) -> None:
        """Stop current animation for drone"""
        if drone_id in self.animations:
            del self.animations[drone_id]