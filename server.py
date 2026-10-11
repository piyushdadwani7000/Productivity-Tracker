"""
================================================================================
FocusTracker Pro — FastAPI HTTP & WebSocket Server (server.py)
================================================================================
Role:
  Acts as the communication and presentation backbone for FocusTracker Pro.
  
Key Responsibilities:
  1. Serves the Single Page Application (HTML, CSS, JS) from the `static/` directory.
  2. Provides real-time bi-directional WebSocket streaming (`/ws`) for live window radar,
     duration tickers, focus score updates, and distraction/milestone alerts.
  3. Provides a full REST API for:
     - Dashboard summaries & 24-hour hourly timeline graphs
     - Activity logging and Human-in-the-Loop AI reclassification
     - Daily task checklists (add, toggle, delete)
     - ML keyword dictionary management & on-demand retraining
     - User settings (idle threshold, distraction alert threshold)
     - Engine tracking controls (start, pause, reset)
  4. Bridges synchronous background events from `TrackingEngine` thread
     into the asynchronous `asyncio` WebSocket event loop thread-safely.

Linkages:
  - Imported and invoked by `app.py` via `run_server(port, open_browser)`.
  - Instantiates and controls `TrackingEngine` (from `tracker.py`).
  - Calls `database.py` for queries, task management, and data resets.
  - Consumed on client side by `static/js/app.js` via REST and WebSocket `/ws`.
================================================================================
"""

import os
import sys
import time
import asyncio
import webbrowser
from datetime import date, datetime
from typing import List, Optional

# -----------------------------------------------------------------------------
# Section 1: Windows Console UTF-8 Configuration
# -----------------------------------------------------------------------------
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
from tracker import TrackingEngine

# -----------------------------------------------------------------------------
# Section 2: Database Initialization & FastAPI Application Setup
# -----------------------------------------------------------------------------
# Ensure SQLite tables and seed keywords exist before routes start taking traffic
database.init_db()

app = FastAPI(
    title="FocusTracker Web", 
    version="2.0.0",
    description="Real-time productivity monitor with machine learning and web rail guard"
)

# Enable CORS for local development and modular testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve static directory whether running as Python script or packaged PyInstaller binary
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BUNDLE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Section 3: Pydantic Request Models (Schema Validation)
# -----------------------------------------------------------------------------
class TaskCreate(BaseModel):
    task_name: str
    date_str: Optional[str] = None

class TaskStatusUpdate(BaseModel):
    status: str  # "pending" or "complete"

class KeywordCreate(BaseModel):
    keyword_phrase: str
    category: str  # "Intended Task" or "Distraction"

class ReclassifyRequest(BaseModel):
    category: str  # "Intended Task" or "Distraction"

class SettingsUpdate(BaseModel):
    idle_threshold: Optional[int] = None
    alert_threshold: Optional[int] = None

class TrackerControl(BaseModel):
    action: str  # "start", "stop", or "toggle"

# -----------------------------------------------------------------------------
# Section 4: WebSocket Connection Manager
# -----------------------------------------------------------------------------
class ConnectionManager:
    """
    Manages active WebSocket client connections and provides thread-safe broadcasting
    from background tracking worker threads into FastAPI's asyncio event loop.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop = None

    def set_loop(self, loop):
        """Captures the active asyncio event loop during application startup."""
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new client WebSocket."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Unregisters a disconnected client WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Sends a JSON message to all currently connected WebSocket clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_sync(self, message: dict):
        """
        Thread-safe bridge method: schedules an async broadcast on the main event
        loop from any external worker thread (such as the TrackingEngine loop).
        """
        if self._loop and self._loop.is_running() and self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)

manager = ConnectionManager()

# -----------------------------------------------------------------------------
# Section 5: Engine Callback Bridges (Tracker Thread -> WebSockets)
# -----------------------------------------------------------------------------
def on_status_update(state: dict):
    """Pushes live active window info and railguard metadata to the web UI."""
    manager.broadcast_sync({
        "type": "live_status",
        "data": state
    })

def on_dashboard_update():
    """Pushes recomputed daily metrics (productive time, focus score) to clients."""
    today = date.today().isoformat()
    summary = database.get_daily_summary(today)
    manager.broadcast_sync({
        "type": "dashboard_stats",
        "data": summary
    })

def on_distraction_alert(window_title: str, duration_secs: int):
    """Pushes distraction warnings when user remains distracted beyond threshold."""
    manager.broadcast_sync({
        "type": "distraction_alert",
        "data": {
            "window_title": window_title,
            "duration_seconds": duration_secs,
            "message": f"Distraction warning! You've spent {duration_secs}s on '{window_title}'. Time to focus!"
        }
    })

def on_5hr_summary():
    """Pushes celebratory milestone notifications upon reaching 5 hours active session."""
    manager.broadcast_sync({
        "type": "milestone_alert",
        "data": {
            "message": "5-Hour Active Milestone reached! Great job! Check your focus score."
        }
    })

# -----------------------------------------------------------------------------
# Section 6: TrackingEngine Instantiation & Application Lifecycle Hooks
# -----------------------------------------------------------------------------
tracker = TrackingEngine(
    callback_update_dashboard=on_dashboard_update,
    callback_distraction_alert=on_distraction_alert,
    callback_5hr_summary=on_5hr_summary,
    callback_status_update=on_status_update,
    idle_threshold=60,
    alert_threshold=30
)

@app.on_event("startup")
async def startup_event():
    """Starts the engine and binds the running asyncio loop upon server boot."""
    manager.set_loop(asyncio.get_running_loop())
    tracker.start()
    print("⚡ FocusTracker Engine started successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully halts the background tracking thread upon server termination."""
    tracker.stop()
    print("FocusTracker Engine stopped.")

# -----------------------------------------------------------------------------
# Section 7: WebSocket Endpoint (/ws)
# -----------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Bi-directional communication channel with client browsers.
    Immediately streams initial state snapshot upon connection, then maintains heartbeats.
    """
    await manager.connect(websocket)
    try:
        # Send initial snapshot immediately upon handshake
        today = date.today().isoformat()
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "live": tracker.get_live_state(),
                "summary": database.get_daily_summary(today),
                "is_running": tracker.running
            }
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# -----------------------------------------------------------------------------
# Section 8: REST API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/status")
def get_live_status():
    """Returns current foreground window metadata and monitoring run status."""
    return {
        "live": tracker.get_live_state(),
        "is_running": tracker.running
    }

@app.get("/api/stats/summary")
def get_stats_summary(day: Optional[str] = None):
    """Returns high-level totals (productive time, distraction time, focus score)."""
    target_day = day or date.today().isoformat()
    return database.get_daily_summary(target_day)

@app.post("/api/stats/reset")
def reset_stats():
    """Clears today's activity sessions and resets counters to zero."""
    today = date.today().isoformat()
    database.reset_today_data(today)
    
    # Reset in-memory session accumulators
    tracker.active_session_time = 0
    tracker.distraction_duration = 0
    tracker.window_start_time = time.time()
    
    on_dashboard_update()
    return {"status": "success", "message": "Today's tracking metrics reset to zero."}

@app.get("/api/stats/hourly")
def get_hourly_stats(day: Optional[str] = None):
    """Returns productive vs distraction duration across 24 hourly buckets."""
    target_day = day or date.today().isoformat()
    return database.get_hourly_breakdown(target_day)

@app.get("/api/activities")
def get_activities(limit: int = 50, search: Optional[str] = None, category: Optional[str] = None):
    """Queries logged window events with optional text search and category filter."""
    activities = database.get_recent_activities(limit=limit)
    if search:
        s = search.lower()
        activities = [a for a in activities if s in a['window_title'].lower() or s in a['app_name'].lower()]
    if category and category != "all":
        activities = [a for a in activities if a['category'].lower() == category.lower()]
    return activities

@app.post("/api/activities/{activity_id}/reclassify")
def reclassify_activity(activity_id: int, req: ReclassifyRequest):
    """
    Human-in-the-Loop feedback: Updates an activity's category, logs feedback,
    adds the title to training keywords, and retrains the Naive Bayes model.
    """
    if req.category not in ["Intended Task", "Distraction"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    database.update_activity_category(activity_id, req.category)
    tracker.force_retrain()
    on_dashboard_update()
    return {"status": "success", "category": req.category}

@app.get("/api/tasks")
def get_tasks(day: Optional[str] = None):
    """Fetches task checklist for the specified day."""
    target_day = day or date.today().isoformat()
    return database.get_tasks(target_day)

@app.post("/api/tasks")
def create_task(req: TaskCreate):
    """Creates a new task item on today's focus list."""
    target_day = req.date_str or date.today().isoformat()
    task_id = database.add_task(req.task_name, target_day)
    return {"status": "success", "id": task_id, "task_name": req.task_name}

@app.put("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: int, req: TaskStatusUpdate):
    """Toggles task status between 'pending' and 'complete'."""
    database.update_task_status(task_id, req.status)
    return {"status": "success", "id": task_id, "status": req.status}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    """Deletes a task by ID."""
    database.delete_task(task_id)
    return {"status": "success", "id": task_id}

@app.get("/api/keywords")
def get_keywords():
    """Lists all training phrases currently stored in SQLite."""
    return database.get_keywords_detailed()

@app.post("/api/keywords")
def create_keyword(req: KeywordCreate):
    """Adds a new training keyword phrase and triggers model retraining."""
    if not req.keyword_phrase.strip():
        raise HTTPException(status_code=400, detail="Phrase cannot be empty")
    database.add_keyword(req.keyword_phrase.strip(), req.category, by_user=True)
    tracker.force_retrain()
    return {"status": "success", "phrase": req.keyword_phrase, "category": req.category}

@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: int):
    """Deletes a training keyword phrase and retrains the model."""
    database.delete_keyword(keyword_id)
    tracker.force_retrain()
    return {"status": "success", "id": keyword_id}

@app.post("/api/model/retrain")
def retrain_model():
    """Explicitly triggers Scikit-Learn model retraining against database keywords."""
    tracker.force_retrain()
    return {"status": "success", "message": "ML classifier retrained successfully on latest database keywords."}

@app.post("/api/settings")
def update_settings(req: SettingsUpdate):
    """Updates idle time and distraction alert thresholds."""
    tracker.set_thresholds(idle_threshold=req.idle_threshold, alert_threshold=req.alert_threshold)
    return {
        "status": "success",
        "idle_threshold": tracker.idle_threshold,
        "alert_threshold": tracker.alert_threshold
    }

@app.post("/api/tracker/control")
def control_tracker(req: TrackerControl):
    """Controls the background tracking engine (start, stop, toggle)."""
    if req.action == "start":
        if not tracker.running:
            tracker.start()
    elif req.action == "stop":
        if tracker.running:
            tracker.stop()
    elif req.action == "toggle":
        if tracker.running:
            tracker.stop()
        else:
            tracker.start()
    return {"status": "success", "is_running": tracker.running}

# -----------------------------------------------------------------------------
# Section 9: Static File Mount & Single Page Application Serving
# -----------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    """Serves the main single-page application entry point (index.html)."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "FocusTracker backend running. static/index.html not found."})

# -----------------------------------------------------------------------------
# Section 10: Server Runner Routine
# -----------------------------------------------------------------------------
def run_server(port: int = 8000, open_browser: bool = True):
    """
    Starts the Uvicorn ASGI server and optionally auto-launches the browser tab.
    
    :param port: TCP listening port (default: 8000).
    :param open_browser: Whether to open default browser on launch.
    """
    url = f"http://localhost:{port}"
    if open_browser:
        def _open():
            time.sleep(1.2)
            webbrowser.open(url)
        import threading
        threading.Thread(target=_open, daemon=True).start()
    
    print(f"\n=======================================================")
    print(f"🚀 FocusTracker Web App running at: {url}")
    print(f"=======================================================\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    run_server(port=8000, open_browser=True)
