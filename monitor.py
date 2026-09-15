import time
import os
import sys

# Platform specific imports for Windows
if sys.platform == 'win32':
    import pygetwindow as gw
    import psutil
    import win32api
    import win32gui
    import win32process
else:
    print("Warning: This module is intended for Windows. Stubbing out functions for non-Windows platforms.")

class SystemMonitor:
    def __init__(self, idle_threshold=60):
        self.idle_threshold = idle_threshold
    
    def get_active_window_info(self):
        """Returns (window_title, app_name, is_split_screen)"""
        if sys.platform != 'win32':
            # Dummy data for non-Windows dev environments
            return "Dummy Window Title", "DummyApp.exe", False
            
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "Unknown", "Unknown", False
                
            window_title = win32gui.GetWindowText(hwnd)
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                app_name = process.name()
            except psutil.NoSuchProcess:
                app_name = "Unknown"
                
            # Split-screen naive check: if window is not maximized and takes up approx half screen width
            is_split_screen = False
            # This can be expanded based on window geometry (win32gui.GetWindowRect)
            
            return window_title, app_name, is_split_screen
        except Exception as e:
            print(f"Error getting active window: {e}")
            return "Unknown", "Unknown", False

    def get_idle_time(self):
        """Returns the number of seconds the system has been idle (no mouse/keyboard input)"""
        if sys.platform != 'win32':
            return 0
            
        try:
            last_input_time = win32api.GetLastInputInfo()
            current_time = win32api.GetTickCount()
            idle_time_ms = current_time - last_input_time
            return idle_time_ms / 1000.0
        except Exception as e:
            print(f"Error getting idle time: {e}")
            return 0

    def is_idle(self):
        return self.get_idle_time() >= self.idle_threshold

if __name__ == "__main__":
    monitor = SystemMonitor(idle_threshold=5)
    print("Monitoring active window for 10 seconds...")
    for _ in range(10):
        title, app, split = monitor.get_active_window_info()
        idle_time = monitor.get_idle_time()
        print(f"[{idle_time:.1f}s idle] Active: {app} - {title} (Split: {split})")
        time.sleep(1)
