@echo off
echo 🚁 RoboMaster TT 3D Simulator - Virtual Environment Setup
echo ============================================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo ✅ Python found: 
python --version

REM Check if virtual environment exists and is functional
if exist "venv" (
    if exist "venv\Scripts\pip.exe" (
        echo 📁 Virtual environment already exists and is functional
    ) else (
        echo 📁 Virtual environment exists but pip is missing, recreating...
        rmdir /s /q venv
        goto create_venv
    )
) else (
    :create_venv
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment, trying alternative...
        python -m venv venv
        if errorlevel 1 (
            echo ❌ Virtual environment creation failed
            pause
            exit /b 1
        )
    )
    echo ✅ Virtual environment created successfully
    

)

REM Check if pip exists and upgrade it
if exist "venv\Scripts\pip.exe" (
    echo 📦 Upgrading pip...
    venv\Scripts\pip install --upgrade pip
    if errorlevel 1 (
        echo ❌ Failed to upgrade pip
        pause
        exit /b 1
    )
    echo ✅ Pip upgraded successfully
) else (
    echo ❌ Pip not found in virtual environment
    echo Trying to install pip manually...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py'"
    venv\Scripts\python get-pip.py
    if errorlevel 1 (
        echo ❌ Failed to install pip
        pause
        exit /b 1
    )
    del get-pip.py
    echo ✅ Pip installed successfully
    
    REM Try upgrading pip again
    venv\Scripts\pip install --upgrade pip
    if errorlevel 1 (
        echo ❌ Failed to upgrade pip
        pause
        exit /b 1
    )
    echo ✅ Pip upgraded successfully
)

REM Install dependencies
echo 📦 Installing dependencies...
venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed successfully

echo.
echo ============================================================
echo 🎉 Virtual environment setup completed successfully!
echo.
echo 📋 Next steps:
echo 1. Activate the virtual environment:
echo    venv\Scripts\activate
echo.
echo 2. Start the simulator:
echo    venv\Scripts\python scripts/start_simulation.py
echo.
echo 3. Or use the provided batch file:
echo    run_in_venv.bat
echo.
echo 4. Open your browser to:
echo    http://localhost:8000
echo.
echo 💡 The virtual environment keeps all dependencies isolated!
echo.
pause