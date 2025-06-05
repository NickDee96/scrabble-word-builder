@echo off
echo ===============================================
echo     Scrabble Word Builder - Service Launcher
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js and try again.
    pause
    exit /b 1
)

echo ✓ Python and Node.js are available
echo.

REM Check if required files exist
if not exist "app.py" (
    echo ERROR: app.py not found
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ERROR: frontend\package.json not found
    echo Please ensure the frontend directory exists.
    pause
    exit /b 1
)

echo ✓ Required files found
echo.

echo Starting Flask backend on port 5000...
start "Scrabble Backend" cmd /k "cd /d "%~dp0" && echo Starting Flask Backend... && python app.py"

echo.
echo Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak > nul

echo.
echo Starting Next.js frontend on port 3000...
start "Scrabble Frontend" cmd /k "cd /d "%~dp0frontend" && echo Starting Next.js Frontend... && npm run dev"

echo.
echo ===============================================
echo Both services are starting...
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo The applications will open in separate windows.
echo Wait a moment for them to fully load.
echo ===============================================
echo.
echo Press any key to close this launcher window
echo (services will continue running in their own windows)
pause >nul
pause > nul
