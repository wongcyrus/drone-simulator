@echo off
echo 🚁 RoboMaster TT 3D Simulator - Virtual Environment Runner
echo ============================================================

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo Please run setup first: python setup_venv.py
    pause
    exit /b 1
)

REM Activate virtual environment
echo 📦 Activating virtual environment...
call venv\Scripts\activate.bat

REM Check activation
if "%VIRTUAL_ENV%"=="" (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated: %VIRTUAL_ENV%

REM Start the simulator
echo.
echo 🚀 Starting RoboMaster TT 3D Simulator...
echo Backend server will be available at: http://localhost:8000
echo Press Ctrl+C to stop the simulation
echo.

python scripts/start_simulation.py --drones 3

REM Deactivate when done
echo.
echo 📦 Deactivating virtual environment...
deactivate

pause