@echo off
setlocal EnableDelayedExpansion
title FocusTracker Setup ^& Installer

echo ======================================================================
echo             ⚡ FocusTracker Pro — Automated Installer
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR:~0,-1%"

:: Check if standalone exe already exists
if exist "%APP_DIR%\dist\FocusTracker.exe" (
    echo [INFO] Found pre-compiled standalone FocusTracker.exe.
    set "TARGET_EXE=%APP_DIR%\dist\FocusTracker.exe"
    goto :CREATE_SHORTCUTS
)

:: Otherwise, check Python and set up environment
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python was not found in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

echo [2/3] Setting up Python virtual environment and dependencies...
if not exist "%APP_DIR%\venv\Scripts\python.exe" (
    echo Creating virtual environment in .\venv...
    python -m venv "%APP_DIR%\venv"
)

echo Installing / updating required packages...
"%APP_DIR%\venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%APP_DIR%\venv\Scripts\python.exe" -m pip install --quiet -r "%APP_DIR%\requirements.txt"

set "TARGET_EXE=%APP_DIR%\run.bat"

:CREATE_SHORTCUTS
echo.
echo [3/3] Creating Desktop and Start Menu Shortcuts...

:: Create run.bat launcher if not exists
if not exist "%APP_DIR%\run.bat" (
    (
        echo @echo off
        echo cd /d "%%~dp0"
        echo if exist "dist\FocusTracker.exe" ^(
        echo     start "" "dist\FocusTracker.exe"
        echo ^) else ^(
        echo     start "" "venv\Scripts\python.exe" app.py
        echo ^)
    ) > "%APP_DIR%\run.bat"
)

:: Create Desktop shortcut via PowerShell
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\FocusTracker.lnk"
set "START_MENU_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\FocusTracker.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%SHORTCUT_PATH%'); " ^
    "$s.TargetPath = '%TARGET_EXE%'; " ^
    "$s.WorkingDirectory = '%APP_DIR%'; " ^
    "$s.Description = 'FocusTracker — AI Productivity Monitor'; " ^
    "$s.Save(); " ^
    "$s2 = $ws.CreateShortcut('%START_MENU_PATH%'); " ^
    "$s2.TargetPath = '%TARGET_EXE%'; " ^
    "$s2.WorkingDirectory = '%APP_DIR%'; " ^
    "$s2.Description = 'FocusTracker — AI Productivity Monitor'; " ^
    "$s2.Save();"

echo.
echo ======================================================================
echo  ✅ Installation Complete!
echo  📌 Desktop Shortcut created: %SHORTCUT_PATH%
echo  🚀 Launching FocusTracker now...
echo ======================================================================
echo.

:: Launch the application
if exist "%APP_DIR%\dist\FocusTracker.exe" (
    start "" "%APP_DIR%\dist\FocusTracker.exe"
) else (
    start "" "%APP_DIR%\venv\Scripts\python.exe" "%APP_DIR%\app.py"
)

exit /b 0
