"""
================================================================================
FocusTracker Pro — Core Tracking Engine (tracker.py)
================================================================================
Role:
  Orchestrates the real-time background tracking lifecycle. Runs a 1.0s polling
  daemon thread that:
    1. Interrogates `SystemMonitor` for active foreground window and idle status.
    2. Detects window focus transitions, calculating duration and closing sessions.
    3. Triggers `classifier.py` for preliminary classification from window title.
    4. Dispatches non-blocking async inspection via `web_inspector.py` for web browsers.
    5. Measures continuous distraction duration and fires native OS and WebSocket alerts.
    6. Persists session records and aggregate daily statistics to `database.py`.

Linkages:
  - Uses `SystemMonitor` (from `monitor.py`) for low-level OS introspection.
  - Uses `WindowClassifier` (from `classifier.py`) for machine learning inference.
  - Uses `WebInspectorBot` (from `web_inspector.py`) for 70-word web rail guard scraping.
  - Uses `database.py` for persistent logging and summary calculations.
  - Controlled by `server.py` (`tracker.start()`, `tracker.stop()`, callbacks).
================================================================================
"""

import time
import sys
import threading
from datetime import datetime, date
from monitor import SystemMonitor
from classifier import WindowClassifier
from web_inspector import WebInspectorBot
import database

# -----------------------------------------------------------------------------
# Section 1: Native Windows OS Topmost Distraction Prompt
# -----------------------------------------------------------------------------
def show_native_distraction_prompt(window_title: str, duration_sec: int):
    """
    Displays a native Windows topmost warning dialog box that automatically
    dismisses itself after 7 seconds so it doesn't permanently block the screen.
    
    Uses Win32 user32.MessageBoxTimeoutW via ctypes.
    """
    if sys.platform == 'win32':
        def _dialog():
            try:
                import ctypes
                MB_ICONWARNING = 0x30
                MB_TOPMOST = 0x40000
                MB_SETFOREGROUND = 0x10000
                clean_title = window_title if len(window_title) <= 60 else window_title[:57] + "..."
                msg = (
                    f"⚠️ You are distracted!\n\n"
                    f"You have spent {duration_sec}s on:\n"
                    f"\"{clean_title}\"\n\n"
                    f"Time to get back to your focus task!"
                )
                ctypes.windll.user32.MessageBoxTimeoutW(
                    0,
                    msg,
                    "FocusTracker — Distraction Warning",
                    MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND,
                    0,
                    7000  # 7-second auto dismiss timeout
                )
            except Exception:
                pass
        threading.Thread(target=_dialog, daemon=True).start()

# -----------------------------------------------------------------------------
# Section 2: TrackingEngine Class
# -----------------------------------------------------------------------------
class TrackingEngine:
    """
    Core engine managing the continuous background monitoring loop,
    window state machine, and bridge to web clients via WebSocket callbacks.
    """

    def __init__(
        self, 
        callback_update_dashboard=None, 
        callback_distraction_alert=None, 
        callback_5hr_summary=None, 
        callback_status_update=None, 
        idle_threshold=60, 
        alert_threshold=30
    ):
        """
        Initializes sub-components and default thresholds.
        
        :param idle_threshold: Seconds of no mouse/key input before marking system as Idle.
        :param alert_threshold: Consecutive distraction seconds before firing alerts.
        """
        self.idle_threshold = idle_threshold
        self.alert_threshold = alert_threshold
        
        # Sub-systems
        self.monitor = SystemMonitor(idle_threshold=self.idle_threshold)
        self.classifier = WindowClassifier()
        self.inspector = WebInspectorBot(max_words=70)
        self.running = False
        self.thread = None
        
        # UI / WebSocket Callback hooks provided by server.py
        self.callback_update_dashboard = callback_update_dashboard
        self.callback_distraction_alert = callback_distraction_alert
        self.callback_5hr_summary = callback_5hr_summary
        self.callback_status_update = callback_status_update
        
        # Live State Machine variables
        self.current_hwnd = 0
        self.current_window = "Initializing..."
        self.current_app = "System"
        self.current_category = "Idle"
        self.current_confidence = 1.0
        self.is_split_screen = False
        self.window_start_time = time.time()
        self.is_idle = False
        
        # Web Rail Guard live metadata
        self.current_url = ""
        self.current_snippet = ""
        self.current_word_count = 0
        self.railguard_triggered = False
        self.matched_keywords = []
        
        # Timers and session metrics
        self.distraction_duration = 0
        self.active_session_time = 0  # Accumulator for 5-hour milestone
        self.last_dashboard_update = time.time()
        
        # Daily summary initialization
        self.today = date.today().isoformat()
        self.init_daily_summary()

    def set_thresholds(self, idle_threshold=None, alert_threshold=None):
        """
        Dynamically updates idle and distraction warning thresholds from settings UI.
        """
        if idle_threshold is not None:
            self.idle_threshold = max(5, int(idle_threshold))
            self.monitor.idle_threshold = self.idle_threshold
        if alert_threshold is not None:
            self.alert_threshold = max(10, int(alert_threshold))

    def init_daily_summary(self):
        """
        Ensures a record exists in `daily_summary` for today's calendar date.
        """
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO daily_summary (date) VALUES (?)
        ''', (self.today,))
        conn.commit()
        conn.close()

    def get_live_state(self):
        """
        Serializes current window status and railguard metadata for WebSocket broadcasting.
        """
        elapsed = time.time() - self.window_start_time if self.window_start_time else 0
        return {
            'window_title': self.current_window,
            'app_name': self.current_app,
            'category': self.current_category,
            'confidence': self.current_confidence,
            'is_split_screen': self.is_split_screen,
            'duration_seconds': max(0, int(elapsed)),
            'is_idle': self.is_idle,
            'idle_time': round(self.monitor.get_idle_time(), 1),
            'idle_threshold': self.idle_threshold,
            'alert_threshold': self.alert_threshold,
            # Web Rail Guard metadata
            'url': self.current_url,
            'snippet': self.current_snippet,
            'word_count': self.current_word_count,
            'railguard_triggered': self.railguard_triggered,
            'matched_keywords': [k[0] if isinstance(k, (tuple, list)) else str(k) for k in self.matched_keywords]
        }

    # -------------------------------------------------------------------------
    # Lifecycle Controls (Start / Stop)
    # -------------------------------------------------------------------------
    def start(self):
        """
        Spawns the background tracking worker thread.
        """
        if not self.running:
            self.running = True
            self.window_start_time = time.time()
            self.current_window = "Resuming Tracking..."
            self.current_app = "System"
            self.current_category = "Idle"
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            if self.callback_status_update:
                self.callback_status_update(self.get_live_state())

    def stop(self):
        """
        Gracefully pauses monitoring and records any open window session.
        """
        if self.running:
            self.running = False
            self._close_current_window_session()
            self.current_window = "Tracking Paused"
            self.current_app = "System"
            self.current_category = "Idle"
            self.current_confidence = 1.0
            self.current_url = ""
            self.current_snippet = ""
            self.distraction_duration = 0
            if self.callback_status_update:
                self.callback_status_update(self.get_live_state())
            if self.thread:
                self.thread.join(timeout=1.0)

    # -------------------------------------------------------------------------
    # Asynchronous Web Inspection Callback
    # -------------------------------------------------------------------------
    def _on_web_inspection_complete(self, target_window: str, inspection_data: dict):
        """
        Callback invoked when the asynchronous 70-word web inspection finishes.
        Updates model prediction using the combined text (window title + 70 words).
        """
        # Ensure user has not switched away to another window while scraping was occurring
        if self.current_window == target_window and not self.is_idle:
            snippet = inspection_data.get('snippet', '')
            url = inspection_data.get('url', '')
            word_count = inspection_data.get('word_count', 0)
            
            # Re-predict using combined title + scraped body words
            cat, conf, matched, overruled = self.classifier.predict(target_window, snippet)
            
            self.current_category = cat
            self.current_confidence = conf
            self.current_url = url
            self.current_snippet = snippet
            self.current_word_count = word_count
            self.railguard_triggered = overruled
            self.matched_keywords = matched
            
            # Reset distraction timer if now categorized as Intended Task
            if cat == "Intended Task":
                self.distraction_duration = 0

            # Push live update to UI via WebSockets
            if self.callback_status_update:
                self.callback_status_update(self.get_live_state())
            if self.callback_update_dashboard:
                self.callback_update_dashboard()

    # -------------------------------------------------------------------------
    # Main Background Polling Loop
    # -------------------------------------------------------------------------
    def _run_loop(self):
        """
        Runs continuously every 1.0 second while `self.running` is True.
        """
        POLL_INTERVAL = 1.0  # Polling interval in seconds
        
        while self.running:
            try:
                # 1. Midnight rollover check
                current_date = date.today().isoformat()
                if current_date != self.today:
                    self.today = current_date
                    self.init_daily_summary()
                    self.active_session_time = 0
                
                # 2. Inactivity / Idle check
                idle_time = self.monitor.get_idle_time()
                if idle_time >= self.monitor.idle_threshold:
                    if not self.is_idle:
                        # User just went idle: close existing window session
                        self._close_current_window_session()
                        self.is_idle = True
                        self.current_window = "System Idle"
                        self.current_app = "System"
                        self.current_category = "Idle"
                        self.current_confidence = 1.0
                        self.current_url = ""
                        self.current_snippet = ""
                        self.current_word_count = 0
                        self.railguard_triggered = False
                        self.matched_keywords = []
                        self.window_start_time = time.time()
                    
                    if self.callback_status_update:
                        self.callback_status_update(self.get_live_state())
                    time.sleep(POLL_INTERVAL)
                    continue
                else:
                    if self.is_idle:
                        # User just returned from idle
                        self.is_idle = False
                        self.window_start_time = time.time()
                    
                # 3. Query OS for active foreground window
                title, app, is_split, hwnd = self.monitor.get_active_window_info()
                self.is_split_screen = is_split
                
                # 4. Check if foreground window transitioned
                if title != self.current_window or self.current_window == "System Idle":
                    # Persist previous window duration to database
                    self._close_current_window_session()
                    
                    self.current_hwnd = hwnd
                    self.current_window = title
                    self.current_app = app
                    self.window_start_time = time.time()
                    self.current_url = ""
                    self.current_snippet = ""
                    self.current_word_count = 0
                    self.railguard_triggered = False
                    self.matched_keywords = []
                    
                    # Preliminary fast classification from window title alone
                    category, confidence, matched, _ = self.classifier.predict(title)
                    self.current_category = category
                    self.current_confidence = confidence
                    self.matched_keywords = matched
                    
                    if category == "Intended Task":
                        self.distraction_duration = 0
                        
                    if self.callback_status_update:
                        self.callback_status_update(self.get_live_state())
                    if self.callback_update_dashboard:
                        self.callback_update_dashboard()

                    # Trigger non-blocking async 70-word web inspection for browsers
                    if self.inspector.is_browser(app) or hwnd > 0:
                        self.inspector.inspect_async(
                            hwnd, app, title,
                            lambda data, t=title: self._on_web_inspection_complete(t, data)
                        )
                else:
                    # 5. User remains on same window: accumulate duration
                    if self.current_category == "Distraction":
                        self.distraction_duration += POLL_INTERVAL
                        
                        # Trigger distraction alerts if continuous threshold reached
                        if self.distraction_duration >= self.alert_threshold:
                            # Alert mechanism 1: Topmost native Windows prompt
                            show_native_distraction_prompt(self.current_window, int(self.distraction_duration))
                            
                            # Alert mechanism 2: WebSocket push to browser dashboard
                            if self.callback_distraction_alert:
                                self.callback_distraction_alert(self.current_window, int(self.distraction_duration))
                                
                            self.distraction_duration = 0  # Reset timer to prevent repeated spam
                            
                    self.active_session_time += POLL_INTERVAL
                    
                    if self.callback_status_update:
                        self.callback_status_update(self.get_live_state())
                    
                    # 6. Check 5-hour active work milestone (18,000 seconds)
                    if self.active_session_time >= 18000 and self.callback_5hr_summary:
                        self.callback_5hr_summary()
                        self.active_session_time = 0
                
                # 7. Periodic dashboard refresh every 3 seconds
                if time.time() - self.last_dashboard_update >= 3:
                    if self.callback_update_dashboard:
                        self.callback_update_dashboard()
                    self.last_dashboard_update = time.time()

            except Exception as e:
                print(f"Error in tracking loop: {e}")

            time.sleep(POLL_INTERVAL)
            
    # -------------------------------------------------------------------------
    # Window Session Closure & Database Persistence
    # -------------------------------------------------------------------------
    def _close_current_window_session(self):
        """
        Calculates duration of finished window session and writes to SQLite database.
        """
        if self.current_window and self.current_window != "System Idle" and self.current_window != "Initializing..." and self.window_start_time:
            end_time = time.time()
            duration = end_time - self.window_start_time
            if duration > 1:  # Filter out transient window switches (<1 second)
                database.log_activity(
                    window_title=self.current_window,
                    app_name=self.current_app,
                    category=self.current_category,
                    start_time=datetime.fromtimestamp(self.window_start_time).isoformat(),
                    end_time=datetime.fromtimestamp(end_time).isoformat(),
                    duration=duration,
                    is_split_screen=self.is_split_screen
                )
                
                # Update today's daily aggregate record
                conn = database.get_connection()
                cursor = conn.cursor()
                if self.current_category == "Distraction":
                    cursor.execute(
                        'UPDATE daily_summary SET total_active_time = total_active_time + ?, total_distraction_time = total_distraction_time + ? WHERE date = ?', 
                        (duration, duration, self.today)
                    )
                else:
                    cursor.execute(
                        'UPDATE daily_summary SET total_active_time = total_active_time + ? WHERE date = ?', 
                        (duration, self.today)
                    )
                conn.commit()
                conn.close()
                
            self.current_window = None
            self.window_start_time = None

    def force_retrain(self):
        """
        Forces the machine learning classifier to retrain on latest database keywords.
        """
        self.classifier.train_model()


