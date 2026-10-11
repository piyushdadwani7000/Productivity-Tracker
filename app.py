"""
================================================================================
FocusTracker Pro — Main CLI Entry Point (app.py)
================================================================================
Role:
  Serves as the root executable script for starting the application from the CLI.
  Parses command-line arguments (such as server port and auto-launch browser flags)
  and triggers the FastAPI/Uvicorn server defined in server.py.

Linkages:
  - Imports `run_server` from `server.py` to launch the backend HTTP & WebSocket server.
  - Executed directly by users via `python app.py`, `run.bat`, or the PyInstaller EXE.
================================================================================
"""

import sys
import os
import argparse

# -----------------------------------------------------------------------------
# Section 1: Windows Console UTF-8 Configuration
# -----------------------------------------------------------------------------
# Fixes UnicodeEncodeError issues when printing Unicode/emojis (e.g., ⚡, 🚀, ⚠️)
# to standard Windows cmd.exe / PowerShell consoles.
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Section 2: Internal Application Imports
# -----------------------------------------------------------------------------
# Imports the main server runner function from server.py which starts FastAPI + Uvicorn
from server import run_server

# -----------------------------------------------------------------------------
# Section 3: CLI Parser and Main Routine
# -----------------------------------------------------------------------------
def main():
    """
    Parses CLI flags and launches the FocusTracker application.
    
    Arguments parsed:
      --port: Custom TCP port for the local web server (defaults to 8000).
      --no-browser: Flag to disable automatic browser tab launch on startup.
    """
    parser = argparse.ArgumentParser(
        description="FocusTracker — Intelligent Productivity & AI Distraction Monitor"
    )
    # Configurable HTTP port
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to run the web server on (default: 8000)"
    )
    # Browser auto-open control
    parser.add_argument(
        "--no-browser", 
        action="store_true", 
        help="Do not automatically open the browser on startup"
    )
    
    args = parser.parse_args()
    
    # Startup banner printed to console
    print("=" * 60)
    print("FocusTracker Web Dashboard starting...")
    print(f"Access in browser at: http://localhost:{args.port}")
    print("=" * 60)
    
    # Hand off control to server.py to boot FastAPI and the background tracking engine
    run_server(port=args.port, open_browser=not args.no_browser)

# Standard Python module execution guard
if __name__ == "__main__":
    main()

