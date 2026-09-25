import sys
import os
import argparse

# Ensure utf-8 stdout on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from server import run_server

def main():
    parser = argparse.ArgumentParser(description="FocusTracker — Intelligent Productivity & AI Distraction Monitor")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the web server on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser on startup")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("FocusTracker Web Dashboard starting...")
    print(f"Access in browser at: http://localhost:{args.port}")
    print("=" * 60)
    
    run_server(port=args.port, open_browser=not args.no_browser)

if __name__ == "__main__":
    main()

