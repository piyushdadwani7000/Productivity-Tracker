import os
import sys
import asyncio
import webbrowser
from datetime import date, datetime
from typing import List, Optional

# Ensure utf-8 stdout on Windows console
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

# Initialize database
database.init_db()

app = FastAPI(title="FocusTracker Web", version="2.0.0")

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BUNDLE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Pydantic models for request bodies
class TaskCreate(BaseModel):
    task_name: str
    date_str: Optional[str] = None

class TaskStatusUpdate(BaseModel):
    status: str

class KeywordCreate(BaseModel):
    keyword_phrase: str
    category: str

class ReclassifyRequest(BaseModel):
    category: str

class SettingsUpdate(BaseModel):
    idle_threshold: Optional[int] = None
    alert_threshold: Optional[int] = None

class TrackerControl(BaseModel):
    action: str  # "start", "stop", "toggle"

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop = None

    def set_loop(self, loop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def broadcast_sync(self, message: dict):
        """Thread-safe broadcast from tracker thread into the asyncio event loop."""
        if self._loop and self._loop.is_running() and self.active_connections:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)

manager = ConnectionManager()

# Tracking Engine callbacks that broadcast to WebSockets
def on_status_update(state: dict):
    manager.broadcast_sync({
        "type": "live_status",
        "data": state
    })

def on_dashboard_update():
    today = date.today().isoformat()
    summary = database.get_daily_summary(today)
    manager.broadcast_sync({
        "type": "dashboard_stats",
        "data": summary
    })

def on_distraction_alert(window_title: str, duration_secs: int):
    manager.broadcast_sync({
        "type": "distraction_alert",
        "data": {
            "window_title": window_title,
            "duration_seconds": duration_secs,
            "message": f"Distraction warning! You've spent {duration_secs}s on '{window_title}'. Time to focus!"
        }
    })

def on_5hr_summary():
    manager.broadcast_sync({
        "type": "milestone_alert",
        "data": {
            "message": "5-Hour Active Milestone reached! Great job! Check your focus score."
        }
    })

# Initialize Tracking Engine with 30s distraction threshold
tracker = TrackingEngine(
    callback_update_dashboard=on_dashboard_update,
    callback_distraction_alert=on_distraction_alert,
    callback_5hr_summary=on_5hr_summary,
    callback_status_update=on_status_update,
    idle_threshold=60,
    alert_threshold=30
)

# Startup event
@app.on_event("startup")
async def startup_event():
    manager.set_loop(asyncio.get_running_loop())
    tracker.start()
    print("⚡ FocusTracker Engine started successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    tracker.stop()
    print("FocusTracker Engine stopped.")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial snapshot immediately
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

# REST API Endpoints

@app.get("/api/status")
def get_live_status():
    return {
        "live": tracker.get_live_state(),
        "is_running": tracker.running
    }

@app.get("/api/stats/summary")
def get_stats_summary(day: Optional[str] = None):
    target_day = day or date.today().isoformat()
    return database.get_daily_summary(target_day)

@app.post("/api/stats/reset")
def reset_stats():
    today = date.today().isoformat()
    database.reset_today_data(today)
    
    # Reset in-memory session counters
    tracker.active_session_time = 0
    tracker.distraction_duration = 0
    tracker.window_start_time = time.time()
    
    on_dashboard_update()
    return {"status": "success", "message": "Today's tracking metrics reset to zero."}

@app.get("/api/stats/hourly")
def get_hourly_stats(day: Optional[str] = None):
    target_day = day or date.today().isoformat()
    return database.get_hourly_breakdown(target_day)

@app.get("/api/activities")
def get_activities(limit: int = 50, search: Optional[str] = None, category: Optional[str] = None):
    activities = database.get_recent_activities(limit=limit)
    if search:
        s = search.lower()
        activities = [a for a in activities if s in a['window_title'].lower() or s in a['app_name'].lower()]
    if category and category != "all":
        activities = [a for a in activities if a['category'].lower() == category.lower()]
    return activities

@app.post("/api/activities/{activity_id}/reclassify")
def reclassify_activity(activity_id: int, req: ReclassifyRequest):
    if req.category not in ["Intended Task", "Distraction"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    database.update_activity_category(activity_id, req.category)
    tracker.force_retrain()
    on_dashboard_update()
    return {"status": "success", "category": req.category}

@app.get("/api/tasks")
def get_tasks(day: Optional[str] = None):
    target_day = day or date.today().isoformat()
    return database.get_tasks(target_day)

@app.post("/api/tasks")
def create_task(req: TaskCreate):
    target_day = req.date_str or date.today().isoformat()
    task_id = database.add_task(req.task_name, target_day)
    return {"status": "success", "id": task_id, "task_name": req.task_name}

@app.put("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: int, req: TaskStatusUpdate):
    database.update_task_status(task_id, req.status)
    return {"status": "success", "id": task_id, "status": req.status}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    database.delete_task(task_id)
    return {"status": "success", "id": task_id}

@app.get("/api/keywords")
def get_keywords():
    return database.get_keywords_detailed()

@app.post("/api/keywords")
def create_keyword(req: KeywordCreate):
    if not req.keyword_phrase.strip():
        raise HTTPException(status_code=400, detail="Phrase cannot be empty")
    database.add_keyword(req.keyword_phrase.strip(), req.category, by_user=True)
    tracker.force_retrain()
    return {"status": "success", "phrase": req.keyword_phrase, "category": req.category}

@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: int):
    database.delete_keyword(keyword_id)
    tracker.force_retrain()
    return {"status": "success", "id": keyword_id}

@app.post("/api/model/retrain")
def retrain_model():
    tracker.force_retrain()
    return {"status": "success", "message": "ML classifier retrained successfully on latest database keywords."}

@app.post("/api/settings")
def update_settings(req: SettingsUpdate):
    tracker.set_thresholds(idle_threshold=req.idle_threshold, alert_threshold=req.alert_threshold)
    return {
        "status": "success",
        "idle_threshold": tracker.idle_threshold,
        "alert_threshold": tracker.alert_threshold
    }

@app.post("/api/tracker/control")
def control_tracker(req: TrackerControl):
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

# Static file serving
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "FocusTracker backend running. static/index.html not found."})

def run_server(port: int = 8000, open_browser: bool = True):
    url = f"http://localhost:{port}"
    if open_browser:
        def _open():
            import time
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
