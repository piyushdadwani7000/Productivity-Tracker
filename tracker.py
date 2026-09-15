import time
import threading
from datetime import datetime, date
from monitor import SystemMonitor
from classifier import WindowClassifier
import database

class TrackingEngine:
    def __init__(self, callback_update_dashboard=None, callback_distraction_alert=None, callback_5hr_summary=None, callback_status_update=None):
        self.monitor = SystemMonitor(idle_threshold=60)
        self.classifier = WindowClassifier()
        self.running = False
        self.thread = None
        
        # Callbacks to UI
        self.callback_update_dashboard = callback_update_dashboard
        self.callback_distraction_alert = callback_distraction_alert
        self.callback_5hr_summary = callback_5hr_summary
        self.callback_status_update = callback_status_update
        
        # State variables
        self.current_window = None
        self.current_category = None
        self.current_confidence = 0.0
        self.window_start_time = None
        
        self.distraction_duration = 0
        self.active_session_time = 0  # To track 5-hour milestone
        self.last_dashboard_update = time.time()
        
        # Ensure daily summary exists
        self.today = date.today().isoformat()
        self.init_daily_summary()

    def init_daily_summary(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO daily_summary (date) VALUES (?)
        ''', (self.today,))
        conn.commit()
        conn.close()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run_loop(self):
        POLL_INTERVAL = 2  # seconds
        
        while self.running:
            # Check for new day
            current_date = date.today().isoformat()
            if current_date != self.today:
                self.today = current_date
                self.init_daily_summary()
                self.active_session_time = 0
            
            idle_time = self.monitor.get_idle_time()
            if idle_time >= self.monitor.idle_threshold:
                # User is idle, pause active tracking and log idle
                if self.current_window is not None:
                    self._close_current_window_session()
                if self.callback_status_update:
                    self.callback_status_update("User Idle", "System", "Idle", 1.0)
                time.sleep(POLL_INTERVAL)
                continue
                
            # Get active window
            title, app, is_split = self.monitor.get_active_window_info()
            
            # If window changed
            if title != self.current_window:
                self._close_current_window_session()
                
                self.current_window = title
                self.window_start_time = time.time()
                
                # Classify
                category, confidence = self.classifier.predict(title)
                self.current_category = category
                self.current_confidence = confidence
                
                # Reset distraction timer if switching to Intended Task
                if category == "Intended Task":
                    self.distraction_duration = 0
                    
                if self.callback_status_update:
                    self.callback_status_update(title, app, category, confidence)
                if self.callback_update_dashboard:
                    self.callback_update_dashboard()
            else:
                # Update duration of current window
                elapsed = time.time() - self.window_start_time
                if self.current_category == "Distraction":
                    self.distraction_duration += POLL_INTERVAL
                    
                    # 2 continuous minutes (120 seconds) on distraction
                    if self.distraction_duration >= 120 and self.callback_distraction_alert:
                        self.callback_distraction_alert(self.current_window)
                        self.distraction_duration = 0  # Reset to avoid spam
                        
                self.active_session_time += POLL_INTERVAL
                
                # Update status with latest live info
                if self.callback_status_update and self.current_window:
                    self.callback_status_update(self.current_window, app, self.current_category, self.current_confidence)
                
                # 5 hours milestone (18000 seconds)
                if self.active_session_time >= 18000 and self.callback_5hr_summary:
                    self.callback_5hr_summary()
                    self.active_session_time = 0
            
            # Dashboard update every 4 seconds
            if time.time() - self.last_dashboard_update >= 4 and self.callback_update_dashboard:
                self.callback_update_dashboard()
                self.last_dashboard_update = time.time()

            time.sleep(POLL_INTERVAL)

            time.sleep(POLL_INTERVAL)
            
    def _close_current_window_session(self):
        if self.current_window and self.window_start_time:
            end_time = time.time()
            duration = end_time - self.window_start_time
            if duration > 1: # Only log if more than 1 sec
                # Get app name
                _, app, is_split = self.monitor.get_active_window_info()
                
                database.log_activity(
                    window_title=self.current_window,
                    app_name=app,
                    category=self.current_category,
                    start_time=datetime.fromtimestamp(self.window_start_time).isoformat(),
                    end_time=datetime.fromtimestamp(end_time).isoformat(),
                    duration=duration,
                    is_split_screen=is_split
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
