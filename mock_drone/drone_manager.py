"""
DroneManager - Manages multiple mock drones with automatic port assignment
"""
import asyncio
import logging
from typing import Dict, List, Optional, Set
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import SimulationConfig
from backend.config import ConfigManager
from .mock_drone import MockDrone


class DroneManager:
    """Manages multiple mock drones with automatic port assignment and coordination"""
    
    def __init__(self, config: Optional[SimulationConfig] = None, backend_url: str = "http://localhost:8000"):
        self.config = config or SimulationConfig()
        self.backend_url = backend_url
        
        # Drone management
        self.drones: Dict[str, MockDrone] = {}
        self.drone_tasks: Dict[str, asyncio.Task] = {}
        self.used_ports: Set[int] = set()
        
        # Port management
        self.base_port = self.config.base_udp_port
        self.max_drones = self.config.max_drones
        self.port_range = range(self.base_port, self.base_port + self.max_drones)
        
        # Manager state
        self.is_running = False
        self.manager_task = None
        
        # Logging
        self.logger = logging.getLogger("DroneManager")
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging for the drone manager"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - DroneManager - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def get_available_port(self) -> Optional[int]:
        """Get the next available UDP port"""
        for port in self.port_range:
            if port not in self.used_ports:
                return port
        return None
    
    def reserve_port(self, port: int) -> bool:
        """Reserve a specific port"""
        if port in self.used_ports or port not in self.port_range:
            return False
        self.used_ports.add(port)
        return True
    
    def release_port(self, port: int) -> None:
        """Release a port back to the available pool"""
        self.used_ports.discard(port)
    
    async def create_drone(self, drone_id: str, port: Optional[int] = None) -> bool:
        """Create a new mock drone with automatic or specified port assignment"""
        if drone_id in self.drones:
            self.logger.warning(f"Drone {drone_id} already exists")
            return False
        
        # Get port
        if port is None:
            port = self.get_available_port()
            if port is None:
                self.logger.error(f"No available ports for drone {drone_id}")
                return False
        else:
            if not self.reserve_port(port):
                self.logger.error(f"Port {port} not available for drone {drone_id}")
                return False
        
        try:
            # Create mock drone
            drone = MockDrone(drone_id, port, self.backend_url, self.config)
            self.drones[drone_id] = drone
            self.used_ports.add(port)
            
            # Start drone in background
            drone_task = asyncio.create_task(self.run_drone(drone_id))
            self.drone_tasks[drone_id] = drone_task
            
            self.logger.info(f"Created drone {drone_id} on port {port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create drone {drone_id}: {e}")
            self.release_port(port)
            return False
    
    async def run_drone(self, drone_id: str):
        """Run a single drone (wrapper for error handling)"""
        drone = self.drones.get(drone_id)
        if not drone:
            return
        
        try:
            await drone.start_udp_server()
        except Exception as e:
            self.logger.error(f"Error running drone {drone_id}: {e}")
        finally:
            # Clean up when drone stops
            await self.remove_drone(drone_id)
    
    async def remove_drone(self, drone_id: str) -> bool:
        """Remove a drone from management"""
        if drone_id not in self.drones:
            self.logger.warning(f"Drone {drone_id} not found for removal")
            return False
        
        try:
            # Stop drone
            drone = self.drones[drone_id]
            await drone.stop()
            
            # Cancel task
            if drone_id in self.drone_tasks:
                task = self.drone_tasks[drone_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.drone_tasks[drone_id]
            
            # Release port
            self.release_port(drone.udp_port)
            
            # Remove from management
            del self.drones[drone_id]
            
            self.logger.info(f"Removed drone {drone_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing drone {drone_id}: {e}")
            return False
    
    async def create_multiple_drones(self, count: int, prefix: str = "drone") -> List[str]:
        """Create multiple drones with automatic naming and port assignment"""
        created_drones = []
        
        for i in range(count):
            drone_id = f"{prefix}_{i + 1}"
            success = await self.create_drone(drone_id)
            if success:
                created_drones.append(drone_id)
            else:
                self.logger.warning(f"Failed to create drone {drone_id}")
                break  # Stop if we can't create more drones
        
        self.logger.info(f"Created {len(created_drones)} drones: {created_drones}")
        return created_drones
    
    def get_drone_info(self, drone_id: str) -> Optional[Dict]:
        """Get information about a specific drone"""
        drone = self.drones.get(drone_id)
        if not drone:
            return None
        
        return {
            "drone_id": drone_id,
            "udp_port": drone.udp_port,
            "backend_url": drone.backend_url,
            "is_running": drone.running,
            "state": {
                "position": {
                    "x": drone.state.position.x,
                    "y": drone.state.position.y,
                    "z": drone.state.position.z
                },
                "is_flying": drone.state.is_flying,
                "is_connected": drone.state.is_connected,
                "battery": drone.state.battery,
                "temperature": drone.state.temperature
            }
        }
    
    def get_all_drone_info(self) -> Dict[str, Dict]:
        """Get information about all managed drones"""
        return {
            drone_id: self.get_drone_info(drone_id)
            for drone_id in self.drones.keys()
        }
    
    def get_status(self) -> Dict:
        """Get overall manager status"""
        return {
            "is_running": self.is_running,
            "total_drones": len(self.drones),
            "max_drones": self.max_drones,
            "used_ports": sorted(list(self.used_ports)),
            "available_ports": [p for p in self.port_range if p not in self.used_ports],
            "base_port": self.base_port,
            "backend_url": self.backend_url
        }
    
    async def start_manager(self):
        """Start the drone manager"""
        if self.is_running:
            self.logger.warning("DroneManager is already running")
            return
        
        self.is_running = True
        self.logger.info("DroneManager started")
        
        # Start monitoring task
        self.manager_task = asyncio.create_task(self.monitor_drones())
    
    async def monitor_drones(self):
        """Monitor drone health and status"""
        while self.is_running:
            try:
                # Check drone health
                failed_drones = []
                for drone_id, task in self.drone_tasks.items():
                    if task.done():
                        # Drone task has finished (likely due to error)
                        failed_drones.append(drone_id)
                
                # Clean up failed drones
                for drone_id in failed_drones:
                    self.logger.warning(f"Drone {drone_id} task finished unexpectedly")
                    await self.remove_drone(drone_id)
                
                # Log status periodically
                if len(self.drones) > 0:
                    self.logger.debug(f"Managing {len(self.drones)} drones on ports: {sorted(self.used_ports)}")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in drone monitoring: {e}")
                await asyncio.sleep(5)
    
    async def stop_manager(self):
        """Stop the drone manager and all drones"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping DroneManager...")
        
        # Stop monitoring task
        if self.manager_task:
            self.manager_task.cancel()
            try:
                await self.manager_task
            except asyncio.CancelledError:
                pass
        
        # Stop all drones
        drone_ids = list(self.drones.keys())
        for drone_id in drone_ids:
            await self.remove_drone(drone_id)
        
        self.logger.info("DroneManager stopped")
    
    async def restart_drone(self, drone_id: str) -> bool:
        """Restart a specific drone"""
        drone_info = self.get_drone_info(drone_id)
        if not drone_info:
            return False
        
        port = drone_info["udp_port"]
        
        # Remove existing drone
        await self.remove_drone(drone_id)
        
        # Create new drone with same port
        return await self.create_drone(drone_id, port)
    
    def list_drones(self) -> List[str]:
        """Get list of all drone IDs"""
        return list(self.drones.keys())
    
    def get_drone_count(self) -> int:
        """Get current number of managed drones"""
        return len(self.drones)
    
    def get_available_port_count(self) -> int:
        """Get number of available ports"""
        return len([p for p in self.port_range if p not in self.used_ports])


async def main():
    """Main function for testing the drone manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RoboMaster TT Drone Manager')
    parser.add_argument('--count', type=int, default=3, help='Number of drones to create')
    parser.add_argument('--prefix', default='drone', help='Drone ID prefix')
    parser.add_argument('--backend', default='http://localhost:8000', help='Backend server URL')
    
    args = parser.parse_args()
    
    # Create configuration
    config = SimulationConfig()
    
    # Create drone manager
    manager = DroneManager(config, args.backend)
    
    try:
        # Start manager
        await manager.start_manager()
        
        # Create drones
        created_drones = await manager.create_multiple_drones(args.count, args.prefix)
        
        if created_drones:
            print(f"Created {len(created_drones)} drones: {created_drones}")
            print(f"Manager status: {manager.get_status()}")
            
            # Keep running
            print("Press Ctrl+C to stop...")
            while manager.is_running:
                await asyncio.sleep(1)
        else:
            print("Failed to create any drones")
            
    except KeyboardInterrupt:
        print("\nShutting down drone manager...")
    finally:
        await manager.stop_manager()


if __name__ == "__main__":
    asyncio.run(main())