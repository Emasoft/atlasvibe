@echo off
setlocal EnableDelayedExpansion

:: AtlasVibe Portable Launcher
:: This script starts AtlasVibe from any location
echo.
echo ============================================
echo   AtlasVibe Portable - Visual Programming IDE
echo ============================================
echo.

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Set the app directory relative to script location
set "APP_DIR=%SCRIPT_DIR%\AtlasVibe-Portable"
set "ELECTRON_EXE=%APP_DIR%\atlasvibe.exe"

:: Check if the executable exists
if not exist "%ELECTRON_EXE%" (
    echo ERROR: AtlasVibe executable not found at:
    echo   %ELECTRON_EXE%
    echo.
    echo Please ensure the AtlasVibe-Portable folder is in the same directory as this script.
    pause
    exit /b 1
)

:: Set environment variables for portable operation
set "PORTABLE_EXECUTABLE_DIR=%APP_DIR%"
set "ELECTRON_RUN_AS_NODE="
set "NODE_ENV=production"

:: Use local paths for Electron
set "APPDATA=%APP_DIR%\appdata"
set "LOCALAPPDATA=%APP_DIR%\localappdata"
set "TEMP=%APP_DIR%\temp"
set "TMP=%APP_DIR%\temp"

:: Create necessary directories if they don't exist
if not exist "%APPDATA%" mkdir "%APPDATA%"
if not exist "%LOCALAPPDATA%" mkdir "%LOCALAPPDATA%"
if not exist "%TEMP%" mkdir "%TEMP%"

:: Add Python to PATH if it exists in resources
if exist "%APP_DIR%\resources\PYTHON" (
    set "PATH=%APP_DIR%\resources\PYTHON;%APP_DIR%\resources\PYTHON\Scripts;%PATH%"
)

:: Log startup information
echo Starting AtlasVibe from: %APP_DIR%
echo Working directory: %CD%
echo.

:: Change to app directory to ensure relative paths work
cd /d "%APP_DIR%"

:: Start AtlasVibe
echo Launching AtlasVibe...
start "" "%ELECTRON_EXE%" %*

:: Return to original directory
cd /d "%SCRIPT_DIR%"

echo.
echo AtlasVibe started successfully!
echo You can close this window.
timeout /t 3 >nul
