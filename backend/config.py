"""
Configuration management for the RoboMaster TT 3D Simulator
"""
import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .models import SimulationConfig


class ConfigManager:
    """Manages configuration loading and saving"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.yaml"
        self.config = SimulationConfig()
        self.load_config()
    
    def load_config(self) -> SimulationConfig:
        """Load configuration from file"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # Create default config file
            self.save_config()
            return self.config
        
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            # Update config with loaded values
            for key, value in data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
        
        return self.config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert config to dictionary
        config_dict = {
            'backend_port': self.config.backend_port,
            'websocket_port': self.config.websocket_port,
            'max_drones': self.config.max_drones,
            'base_udp_port': self.config.base_udp_port,
            'default_speed': self.config.default_speed,
            'gravity': self.config.gravity,
            'air_resistance': self.config.air_resistance,
            'max_acceleration': self.config.max_acceleration,
            'update_rate': self.config.update_rate,
            'battery_drain_rate': self.config.battery_drain_rate,
            'scene_bounds': list(self.config.scene_bounds)
        }
        
        try:
            with open(config_file, 'w') as f:
                if config_file.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2)
                else:
                    yaml.dump(config_dict, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save_config()
    
    def get_config(self) -> SimulationConfig:
        """Get current configuration"""
        return self.config