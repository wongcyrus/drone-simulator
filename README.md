# RoboMaster TT 3D Simulator

A comprehensive 3D simulation environment for RoboMaster TT drones with realistic UDP API mockup, physics simulation, and web-based visualization.

## Features

- 🚁 **Realistic Drone Simulation**: Complete UDP API compatibility with RoboMaster TT protocol
- 🎮 **3D Visualization**: Interactive Three.js-based 3D environment with real-time drone rendering
- 🌐 **Multi-Drone Support**: Simulate multiple drones simultaneously on different ports
- ⚡ **Real-time Updates**: WebSocket communication for live drone state updates
- 🔧 **Physics Engine**: Realistic movement, gravity, flight dynamics, and collision detection
- 📊 **Telemetry Simulation**: Battery, temperature, mission pad detection, and comprehensive sensor data
- 🧪 **Comprehensive Testing**: Full test suite with unit tests and integration tests
- 🔧 **Easy Setup**: Virtual environment setup with batch/shell scripts

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Set up virtual environment (recommended):**
```bash
# Windows
setup_venv.bat

# Linux/Mac
chmod +x setup_venv.sh && ./setup_venv.sh
```

2. **Or install dependencies manually:**
```bash
pip install -r requirements.txt
```

3. **Start the simulation components:**

**Option A: Quick Start (Windows)**
```bash
run_in_venv.bat
```

**Option B: Quick Start (Linux/Mac)**
```bash
./run_in_venv.sh
```

**Option C: Manual startup**
```bash
# Terminal 1: Start backend server
python -m backend.server

# Terminal 2: Start mock drones
python -m mock_drone.drone_manager --count 3

# Or start individual drones:
python -m mock_drone.mock_drone --drone-id drone_1 --port 8889
python -m mock_drone.mock_drone --drone-id drone_2 --port 8890
python -m mock_drone.mock_drone --drone-id drone_3 --port 8891
```

### Access the Simulator

Open your web browser and go to:
```
http://localhost:8000
```

You should see:
- 3D visualization of the simulation environment
- Real-time drone information panel
- Connection status indicator

## Usage

### Testing with Your RoboMaster TT Code

The simulator is fully compatible with existing RoboMaster TT code. Simply change your drone IP addresses to `localhost` and use the assigned ports:

```python
# Example: Connect to simulated drones
import socket

# Drone 1 on port 8889
drone1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
drone1.sendto(b'command', ('localhost', 8889))
response = drone1.recv(1024)
print(response.decode())  # Should print 'ok'

# Send takeoff command
drone1.sendto(b'takeoff', ('localhost', 8889))
response = drone1.recv(1024)
print(response.decode())  # Should print 'ok'
```

### Supported Commands

All standard RoboMaster TT commands are supported:

**Control Commands:**
- `command` - Enter SDK mode
- `takeoff` - Take off
- `land` - Land
- `up x`, `down x`, `left x`, `right x`, `forward x`, `back x` - Move in direction
- `cw x`, `ccw x` - Rotate clockwise/counter-clockwise
- `flip x` - Flip (l/r/f/b)
- `go x y z speed` - Move to relative position
- `curve x1 y1 z1 x2 y2 z2 speed` - Fly in curve

**Setting Commands:**
- `speed x` - Set speed (10-100 cm/s)
- `rc a b c d` - Set RC values
- `wifi ssid pass` - Set WiFi credentials

**Read Commands:**
- `battery?` - Get battery level
- `speed?` - Get current speed
- `time?` - Get flight time
- `temp?` - Get temperature
- `attitude?` - Get pitch, roll, yaw
- And many more...

## Advanced Usage

### Custom Configuration

Edit `config.yaml` to customize:

```yaml
# Server Settings
backend_port: 8000
max_drones: 10
base_udp_port: 8889

# Physics Settings
gravity: 9.81
air_resistance: 0.1
update_rate: 30

# Scene Settings
scene_bounds: [1000, 1000, 500]  # x, y, z in cm
```

### Launch Options

**Backend Server Options:**
```bash
# Start backend on custom port
python -m backend.server --port 8080

# Start with debug logging
python -m backend.server --debug
```

**Mock Drone Manager Options:**
```bash
# Start with 5 drones
python -m mock_drone.drone_manager --count 5

# Use custom starting port
python -m mock_drone.drone_manager --count 3 --start-port 8900

# Custom drone prefix
python -m mock_drone.drone_manager --count 3 --prefix "test_drone"
```

**Individual Mock Drone Options:**
```bash
# Start single drone with custom settings
python -m mock_drone.mock_drone --drone-id my_drone --port 8889 --host 0.0.0.0

# Start drone with custom backend URL
python -m mock_drone.mock_drone --drone-id drone_1 --port 8889 --backend-url http://192.168.1.100:8000
```

### Manual Component Startup

If you prefer to start components separately:

1. **Start Backend Server:**
```bash
python -m backend.server
```

2. **Start Individual Mock Drone:**
```bash
python -m mock_drone.mock_drone --drone-id drone_1 --port 8889
```

3. **Start Multiple Drones with Manager:**
```bash
python -m mock_drone.drone_manager --count 3
```

## Development

### Project Structure

```
├── backend/                    # FastAPI backend server
│   ├── server.py              # Main server application
│   ├── models.py              # Data models and Pydantic schemas
│   ├── config.py              # Configuration management
│   └── __init__.py
├── mock_drone/                 # Mock drone simulation
│   ├── mock_drone.py          # Main drone UDP server simulation
│   ├── physics_engine.py      # Realistic physics simulation
│   ├── telemetry_simulator.py # Sensor data simulation
│   ├── drone_manager.py       # Multi-drone management
│   └── __init__.py
├── frontend/                   # Web-based 3D visualization
│   ├── index.html             # Main HTML page
│   └── js/                    # JavaScript modules
│       ├── main.js            # Application entry point
│       ├── scene3d.js         # Three.js 3D scene management
│       ├── drone-renderer.js  # Drone 3D rendering
│       ├── websocket-client.js # WebSocket communication
│       └── ui-controller.js   # UI management
├── tests/                      # Comprehensive test suite
│   ├── test_mock_drone.py     # Mock drone unit tests
│   ├── test_backend_server.py # Backend API tests
│   ├── test_physics_engine.py # Physics simulation tests
│   ├── test_telemetry_simulator.py # Telemetry tests
│   ├── test_integration.py    # Integration tests
│   └── __init__.py
├── djitellopy/                 # DJI Tello Python library
│   ├── tello.py               # Main Tello class
│   ├── swarm.py               # Swarm functionality
│   └── __init__.py
├── config.yaml                 # Main configuration file
├── requirements.txt            # Python dependencies
├── setup_venv.bat             # Windows virtual environment setup
├── run_in_venv.bat            # Windows quick start script
├── run_in_venv.sh             # Linux/Mac quick start script
├── test_simple_drone.py       # Multi-drone test suite
└── debug_connection.py        # Connection debugging utility
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_mock_drone.py

# Run with coverage
python -m pytest tests/ --cov=mock_drone --cov=backend
```

## Troubleshooting

### Common Issues

1. **Port Already in Use:**
   - Change the backend port: `--port 8001`
   - Check for other applications using ports 8889-8898

2. **Connection Refused:**
   - Ensure backend server is running
   - Check firewall settings
   - Verify correct URL: `http://localhost:8000`

3. **Drones Not Appearing:**
   - Check browser console for errors
   - Verify WebSocket connection (green "Connected" status)
   - Restart the simulation

4. **Performance Issues:**
   - Reduce number of drones: `--drones 2`
   - Close other browser tabs
   - Check system resources

### Debug Mode

Enable debug logging:

```bash
# Windows
set PYTHONPATH=.
python -m backend.server --debug

# Linux/Mac
export PYTHONPATH=.
python -m backend.server --debug
```

**Debug Connection Issues:**
```bash
# Test individual drone connection
python debug_connection.py

# Test with specific drone
python -m mock_drone.mock_drone --drone-id debug_drone --port 8889 --debug

# Run comprehensive multi-drone test
python test_simple_drone.py --mode multi --count 3
```

## API Reference

### Backend API Endpoints

- `GET /api/health` - Health check
- `GET /api/drones` - List all drones
- `GET /api/drones/{drone_id}` - Get specific drone state
- `POST /api/drones/{drone_id}/state` - Update drone state
- `DELETE /api/drones/{drone_id}` - Remove drone
- `GET /api/config` - Get configuration
- `POST /api/config` - Update configuration

### WebSocket Events

- `drone_added` - New drone connected
- `drone_removed` - Drone disconnected
- `drone_state_update` - Real-time state update

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the console logs for error messages
3. Ensure all dependencies are installed correctly
4. Verify your Python version (3.8+ required)