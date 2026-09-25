@echo off
title Building FocusTracker Standalone Executable
echo ========================================================
echo 🔨 Building FocusTracker Standalone Executable (.exe)...
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .\venv.
    echo Please run Install_FocusTracker.bat first.
    pause
    exit /b 1
)

echo [1/2] Installing build tools and dependencies...
venv\Scripts\python.exe -m pip install --quiet pyinstaller fastapi uvicorn[standard] scikit-learn pandas psutil pywin32 beautifulsoup4 uiautomation

echo [2/2] Running PyInstaller build...
venv\Scripts\python.exe -m PyInstaller FocusTracker.spec --noconfirm

if exist "dist\FocusTracker.exe" (
    echo.
    echo ========================================================
    echo ✅ SUCCESS! Executable built at: dist\FocusTracker.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Build failed. Check the logs above.
)

pause
