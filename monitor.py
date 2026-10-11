"""
================================================================================
FocusTracker Pro — Low-Level System Monitor (monitor.py)
================================================================================
Role:
  Interfaces directly with the Microsoft Windows OS via Win32 C-APIs and psutil
  to inspect the active foreground window, resolve process binaries, and track
  system-wide user inactivity (idle time).

Linkages:
  - Instantiated by `TrackingEngine` in `tracker.py` as `self.monitor`.
  - Provides active window information (`window_title`, `app_name`, `hwnd`) to
    `tracker.py`, which then delegates classification and web scraping.
  - Queries Windows user32/kernel32 APIs for hardware input ticks.
================================================================================
"""

import time
import os
import sys

# -----------------------------------------------------------------------------
# Section 1: Platform-Specific Win32 Imports & Non-Windows Fallback
# -----------------------------------------------------------------------------
# FocusTracker relies on low-level Windows User32 and Kernel32 APIs.
# On non-Windows platforms (e.g., Linux/macOS dev containers), stub fallbacks are used.
if sys.platform == 'win32':
    import pygetwindow as gw
    import psutil
    import win32api
    import win32gui
    import win32process
else:
    print("Warning: This module is intended for Windows. Stubbing out functions for non-Windows platforms.")

# -----------------------------------------------------------------------------
# Section 2: SystemMonitor Class
# -----------------------------------------------------------------------------
class SystemMonitor:
    """
    Monitors user activity at the operating system level.
    
    Key Responsibilities:
      1. Foreground Window Detection: Identifies what app and window is currently focused.
      2. Idle Detection: Measures hardware inactivity (keyboard/mouse) using Windows TickCount.
    """

    def __init__(self, idle_threshold=60):
        """
        Initializes the monitor with an idle cutoff threshold.
        
        :param idle_threshold: Inactivity time (in seconds) after which user is considered idle.
        """
        self.idle_threshold = idle_threshold
    
    # -------------------------------------------------------------------------
    # Active Window & Process Inspection
    # -------------------------------------------------------------------------
    def get_active_window_info(self):
        """
        Inspects the current foreground window on Windows desktop.
        
        Returns:
            Tuple of:
              - window_title (str): Title text shown in window title bar / taskbar.
              - app_name (str): Executable name of the host process (e.g., 'chrome.exe', 'Code.exe').
              - is_split_screen (bool): Whether window is tiled/split across screen halves.
              - hwnd (int): Win32 window handle ID (HWND) required for UIAutomation tree traversal.
        """
        if sys.platform != 'win32':
            # Dummy fallback data for non-Windows dev environments
            return "Dummy Window Title", "DummyApp.exe", False, 0
            
        try:
            # 1. Retrieve the Win32 window handle (HWND) for the current foreground window
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "Unknown", "Unknown", False, 0
                
            # 2. Extract the UTF-16 title string of the focused window
            window_title = win32gui.GetWindowText(hwnd)
            
            # 3. Obtain the Process ID (PID) owning this window handle
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                # 4. Resolve PID to executable filename via psutil (e.g., 'chrome.exe', 'slack.exe')
                process = psutil.Process(pid)
                app_name = process.name()
            except psutil.NoSuchProcess:
                app_name = "Unknown"
                
            # 5. Split-screen naive check
            is_split_screen = False
            
            return window_title, app_name, is_split_screen, hwnd
        except Exception as e:
            print(f"Error getting active window: {e}")
            return "Unknown", "Unknown", False, 0

    # -------------------------------------------------------------------------
    # System-Wide Hardware Idle Detection
    # -------------------------------------------------------------------------
    def get_idle_time(self):
        """
        Calculates time elapsed since the last physical user interaction (keyboard or mouse).
        
        Mechanism:
          - `win32api.GetLastInputInfo()` returns the tick count when user last moved mouse/typed.
          - `win32api.GetTickCount()` returns total milliseconds elapsed since system boot.
          - Difference = milliseconds of absolute user inactivity.
        
        Returns:
            Idle duration in seconds as a float.
        """
        if sys.platform != 'win32':
            return 0
            
        try:
            last_input_time = win32api.GetLastInputInfo()
            current_time = win32api.GetTickCount()
            idle_time_ms = current_time - last_input_time
            return max(0.0, idle_time_ms / 1000.0)
        except Exception as e:
            print(f"Error getting idle time: {e}")
            return 0

    def is_idle(self):
        """
        Convenience predicate checking whether current idle time exceeds `self.idle_threshold`.
        """
        return self.get_idle_time() >= self.idle_threshold

# -----------------------------------------------------------------------------
# Section 3: Diagnostic CLI Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    monitor = SystemMonitor(idle_threshold=5)
    print("Monitoring active window for 10 seconds...")
    for _ in range(10):
        title, app, split, hwnd = monitor.get_active_window_info()
        idle_time = monitor.get_idle_time()
        print(f"[{idle_time:.1f}s idle] Active: {app} (HWND: {hwnd}) - {title} (Split: {split})")
        time.sleep(1)
