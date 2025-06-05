@echo off
REM Docker Compose Helper Script for Scrabble Word Builder (Windows)

setlocal enabledelayedexpansion

REM Colors for output (Windows doesn't support colors well, so we'll use plain text)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

REM Function to check if Docker is running
:check_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Docker is not running. Please start Docker and try again.
    exit /b 1
)
echo %SUCCESS% Docker is running
goto :eof

REM Function to check if docker-compose is available
:check_docker_compose
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% docker-compose is not installed. Please install docker-compose and try again.
    exit /b 1
)
echo %SUCCESS% docker-compose is available
goto :eof

REM Function to start services
:start_services
set env=%1
if "%env%"=="" set env=production

echo %INFO% Starting Scrabble Word Builder in %env% mode...

if /i "%env%"=="dev" goto start_dev
if /i "%env%"=="development" goto start_dev
if /i "%env%"=="prod" goto start_prod
if /i "%env%"=="production" goto start_prod
goto start_default

:start_dev
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
goto start_success

:start_prod
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
goto start_success

:start_default
docker-compose up --build -d
goto start_success

:start_success
echo %SUCCESS% Services started successfully!
echo %INFO% Frontend: http://localhost:3000
echo %INFO% Backend API: http://localhost:5000
echo %INFO% Backend Health: http://localhost:5000/api/health
goto :eof

REM Function to stop services
:stop_services
echo %INFO% Stopping Scrabble Word Builder services...
docker-compose down
echo %SUCCESS% Services stopped successfully!
goto :eof

REM Function to show logs
:show_logs
set service=%1
if "%service%"=="" (
    docker-compose logs -f
) else (
    docker-compose logs -f %service%
)
goto :eof

REM Function to show service status
:show_status
echo %INFO% Service Status:
docker-compose ps

echo %INFO% Health Status:
docker-compose exec backend curl -f http://localhost:5000/api/health 2>nul || echo %WARNING% Backend health check failed
docker-compose exec frontend curl -f http://localhost:3000/ 2>nul || echo %WARNING% Frontend health check failed
goto :eof

REM Function to clean up
:cleanup
echo %INFO% Cleaning up Docker resources...
docker-compose down -v --remove-orphans
docker system prune -f
echo %SUCCESS% Cleanup completed!
goto :eof

REM Function to rebuild services
:rebuild
echo %INFO% Rebuilding services...
docker-compose down
docker-compose build --no-cache
docker-compose up -d
echo %SUCCESS% Services rebuilt and started!
goto :eof

REM Function to show help
:show_help
echo Docker Helper Script for Scrabble Word Builder
echo.
echo Usage: %~nx0 [command] [options]
echo.
echo Commands:
echo   start [env]     Start services (env: dev/development, prod/production)
echo   stop            Stop services
echo   restart [env]   Restart services
echo   logs [service]  Show logs (service: backend, frontend, or all)
echo   status          Show service status and health
echo   rebuild         Rebuild and restart services
echo   cleanup         Stop services and clean up Docker resources
echo   help            Show this help message
echo.
echo Examples:
echo   %~nx0 start dev    # Start in development mode
echo   %~nx0 start prod   # Start in production mode
echo   %~nx0 logs backend # Show backend logs
echo   %~nx0 status       # Check service status
goto :eof

REM Main script logic
call :check_docker
if %errorlevel% neq 0 exit /b 1

call :check_docker_compose
if %errorlevel% neq 0 exit /b 1

set command=%1
if "%command%"=="" set command=help

if /i "%command%"=="start" (
    call :start_services %2
) else if /i "%command%"=="stop" (
    call :stop_services
) else if /i "%command%"=="restart" (
    call :stop_services
    call :start_services %2
) else if /i "%command%"=="logs" (
    call :show_logs %2
) else if /i "%command%"=="status" (
    call :show_status
) else if /i "%command%"=="rebuild" (
    call :rebuild
) else if /i "%command%"=="cleanup" (
    call :cleanup
) else if /i "%command%"=="help" (
    call :show_help
) else if /i "%command%"=="--help" (
    call :show_help
) else if /i "%command%"=="-h" (
    call :show_help
) else (
    echo %ERROR% Unknown command: %command%
    call :show_help
    exit /b 1
)
