@echo off
setlocal

echo [DisplayPresets] Starting development environment...
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    echo Install Python 3.10+ and make sure it is added to PATH.
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH.
    echo Install Node.js 20+ from https://nodejs.org
    pause
    exit /b 1
)

:: Quick backend smoke test
echo Checking Python backend...
python -c "from display_presets.server import main" 2>nul
if errorlevel 1 (
    echo ERROR: Could not import display_presets. Make sure you are running this
    echo        from the project root directory.
    pause
    exit /b 1
)
echo Python backend OK.
echo.

:: Install npm dependencies if needed
if not exist "electron-app\node_modules" (
    echo Installing npm dependencies...
    cd electron-app
    npm install
    cd ..
    echo.
)

:: Launch
echo Starting Electron app...
echo   - Vite dev server will start on http://localhost:5173
echo   - Electron will launch once Vite is ready
echo   - Python backend will be spawned automatically by Electron
echo.
echo Press Ctrl+C to stop.
echo.

cd electron-app
npm run electron:dev
