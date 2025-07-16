#!/bin/bash

echo "🚁 RoboMaster TT 3D Simulator - Virtual Environment Runner"
echo "============================================================"

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run setup first: python3 setup_venv.py"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# Start the simulator
echo ""
echo "🚀 Starting RoboMaster TT 3D Simulator..."
echo "Backend server will be available at: http://localhost:8000"
echo "Press Ctrl+C to stop the simulation"
echo ""

python scripts/start_simulation.py --drones 3

# Deactivate when done
echo ""
echo "📦 Deactivating virtual environment..."
deactivate

echo "✅ Simulator stopped"