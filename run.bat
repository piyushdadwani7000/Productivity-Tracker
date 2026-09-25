@echo off
title FocusTracker
cd /d "%~dp0"

if exist "dist\FocusTracker.exe" (
    start "" "dist\FocusTracker.exe"
) else if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\python.exe" app.py
) else (
    start "" python app.py
)
