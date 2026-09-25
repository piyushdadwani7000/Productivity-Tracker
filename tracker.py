import time
import sys
import threading
from datetime import datetime, date
from monitor import SystemMonitor
from classifier import WindowClassifier
from web_inspector import WebInspectorBot
import database

def show_native_distraction_prompt(window_title: str, duration_sec: int):
    """Displays a native Windows topmost alert prompt that auto-closes after 7 seconds."""
    if sys.platform == 'win32':
        def _dialog():
            try:
                import ctypes
                MB_ICONWARNING = 0x30
                MB_TOPMOST = 0x40000
                MB_SETFOREGROUND = 0x10000
                clean_title = window_title if len(window_title) <= 60 else window_title[:57] + "..."
                msg = f"⚠️ You are distracted!\n\nYou have spent {duration_sec}s on:\n\"{clean_title}\"\n\nTime to get back to your focus task!"
                ctypes.windll.user32.MessageBoxTimeoutW(
                    0,
                    msg,
                    "FocusTracker — Distraction Warning",
                    MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND,
                    0,
                    7000  # 7-second auto dismiss
                )
            except Exception:
                pass
        threading.Thread(target=_dialog, daemon=True).start()

class TrackingEngine:
    def __init__(self, callback_update_dashboard=None, callback_distraction_alert=None, callback_5hr_summary=None, callback_status_update=None, idle_threshold=60, alert_threshold=30):
        self.idle_threshold = idle_threshold
        self.alert_threshold = alert_threshold  # Default: 30 seconds
        self.monitor = SystemMonitor(idle_threshold=self.idle_threshold)
        self.classifier = WindowClassifier()
        self.inspector = WebInspectorBot(max_words=70)
        self.running = False
        self.thread = None
        
        # Callbacks to UI / WebSockets
        self.callback_update_dashboard = callback_update_dashboard
        self.callback_distraction_alert = callback_distraction_alert
        self.callback_5hr_summary = callback_5hr_summary
        self.callback_status_update = callback_status_update

        
        # State variables
        self.current_hwnd = 0
        self.current_window = "Initializing..."
        self.current_app = "System"
        self.current_category = "Idle"
        self.current_confidence = 1.0
        self.is_split_screen = False
        self.window_start_time = time.time()
        self.is_idle = False
        
        # Web Railguard inspection state
        self.current_url = ""
        self.current_snippet = ""
        self.current_word_count = 0
        self.railguard_triggered = False
        self.matched_keywords = []
        
        self.distraction_duration = 0
        self.active_session_time = 0  # To track 5-hour milestone
        self.last_dashboard_update = time.time()
        
        # Ensure daily summary exists
        self.today = date.today().isoformat()
        self.init_daily_summary()

    def set_thresholds(self, idle_threshold=None, alert_threshold=None):
        if idle_threshold is not None:
            self.idle_threshold = max(5, int(idle_threshold))
            self.monitor.idle_threshold = self.idle_threshold
        if alert_threshold is not None:
            self.alert_threshold = max(10, int(alert_threshold))

    def init_daily_summary(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO daily_summary (date) VALUES (?)
        ''', (self.today,))
        conn.commit()
        conn.close()

    def get_live_state(self):
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

    def start(self):
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

    def _on_web_inspection_complete(self, target_window: str, inspection_data: dict):
        """Callback invoked when asynchronous 70-word web inspection finishes."""
        # Only apply if user is still on the same window
        if self.current_window == target_window and not self.is_idle:
            snippet = inspection_data.get('snippet', '')
            url = inspection_data.get('url', '')
            word_count = inspection_data.get('word_count', 0)
            
            # Predict using combined title + first 70 words
            cat, conf, matched, overruled = self.classifier.predict(target_window, snippet)
            
            self.current_category = cat
            self.current_confidence = conf
            self.current_url = url
            self.current_snippet = snippet
            self.current_word_count = word_count
            self.railguard_triggered = overruled
            self.matched_keywords = matched
            
            # Reset distraction duration if now Intended Task
            if cat == "Intended Task":
                self.distraction_duration = 0

            # Push live update to UI
            if self.callback_status_update:
                self.callback_status_update(self.get_live_state())
            if self.callback_update_dashboard:
                self.callback_update_dashboard()

    def _run_loop(self):
        POLL_INTERVAL = 1.0  # Snappy 1 second polling
        
        while self.running:
            try:
                # Check for new day
                current_date = date.today().isoformat()
                if current_date != self.today:
                    self.today = current_date
                    self.init_daily_summary()
                    self.active_session_time = 0
                
                idle_time = self.monitor.get_idle_time()
                if idle_time >= self.monitor.idle_threshold:
                    if not self.is_idle:
                        # Transitioning to idle
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
                        self.is_idle = False
                        self.window_start_time = time.time()
                    
                # Get active window info with hwnd
                title, app, is_split, hwnd = self.monitor.get_active_window_info()
                self.is_split_screen = is_split
                
                # If window changed
                if title != self.current_window or self.current_window == "System Idle":
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
                    
                    # Preliminary fast classification from window title
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

                    # Trigger non-blocking async 70-word web inspection
                    if self.inspector.is_browser(app) or hwnd > 0:
                        self.inspector.inspect_async(
                            hwnd, app, title,
                            lambda data, t=title: self._on_web_inspection_complete(t, data)
                        )
                else:
                    # Update live state duration
                    if self.current_category == "Distraction":
                        self.distraction_duration += POLL_INTERVAL
                        
                        # Continuous distraction reaches threshold (e.g. 30s)
                        if self.distraction_duration >= self.alert_threshold:
                            # 1. Native Windows Topmost Prompt
                            show_native_distraction_prompt(self.current_window, int(self.distraction_duration))
                            
                            # 2. Browser WebSocket alert callback
                            if self.callback_distraction_alert:
                                self.callback_distraction_alert(self.current_window, int(self.distraction_duration))
                                
                            self.distraction_duration = 0  # Reset to avoid spam
                            
                    self.active_session_time += POLL_INTERVAL
                    
                    if self.callback_status_update:
                        self.callback_status_update(self.get_live_state())
                    
                    # 5 hours milestone (18000 seconds)
                    if self.active_session_time >= 18000 and self.callback_5hr_summary:
                        self.callback_5hr_summary()
                        self.active_session_time = 0
                
                # Dashboard stats update every 3 seconds
                if time.time() - self.last_dashboard_update >= 3:
                    if self.callback_update_dashboard:
                        self.callback_update_dashboard()
                    self.last_dashboard_update = time.time()

            except Exception as e:
                print(f"Error in tracking loop: {e}")

            time.sleep(POLL_INTERVAL)
            
    def _close_current_window_session(self):
        if self.current_window and self.current_window != "System Idle" and self.current_window != "Initializing..." and self.window_start_time:
            end_time = time.time()
            duration = end_time - self.window_start_time
            if duration > 1:  # Only log if more than 1 sec
                database.log_activity(
                    window_title=self.current_window,
                    app_name=self.current_app,
                    category=self.current_category,
                    start_time=datetime.fromtimestamp(self.window_start_time).isoformat(),
                    end_time=datetime.fromtimestamp(end_time).isoformat(),
                    duration=duration,
                    is_split_screen=self.is_split_screen
                )
                
                # Update daily summary
                conn = database.get_connection()
                cursor = conn.cursor()
                if self.current_category == "Distraction":
                    cursor.execute('UPDATE daily_summary SET total_active_time = total_active_time + ?, total_distraction_time = total_distraction_time + ? WHERE date = ?', (duration, duration, self.today))
                else:
                    cursor.execute('UPDATE daily_summary SET total_active_time = total_active_time + ? WHERE date = ?', (duration, self.today))
                conn.commit()
                conn.close()
                
            self.current_window = None
            self.window_start_time = None

    def force_retrain(self):
        """Forces the classifier to retrain on updated DB keywords."""
        self.classifier.train_model()


