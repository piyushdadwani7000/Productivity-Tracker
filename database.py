"""
================================================================================
FocusTracker Pro — SQLite Database Layer (database.py)
================================================================================
Role:
  Manages persistent storage for FocusTracker using an embedded SQLite database
  (`tracker.db`). Handles database creation, migrations, CRUD operations,
  and aggregation queries for daily summaries and 24-hour hourly timelines.

Database Tables:
  1. `activity_log`: Granular records of active window durations and categories.
  2. `idle_log`: Log of user idle/inactivity durations.
  3. `tasks`: Daily planned tasks, completion status, and time spent.
  4. `breaks`: Scheduled and taken break durations.
  5. `keywords`: Training dictionary phrases and categories for Naive Bayes ML.
  6. `daily_summary`: Aggregated rollups per calendar day (active, distraction, idle).
  7. `classification_feedback`: Audit trail of user reclassifications for model training.

Linkages:
  - Called by `tracker.py` to record completed window sessions and update daily summaries.
  - Called by `classifier.py` to load training keywords (`get_keywords`).
  - Called by `server.py` to service REST endpoints for activities, stats, tasks, and keywords.
================================================================================
"""

import sqlite3
import os
import sys
from datetime import datetime

# -----------------------------------------------------------------------------
# Section 1: Database Path Resolution & Connection Factory
# -----------------------------------------------------------------------------
# Handles running both in standard Python and when bundled inside PyInstaller EXE
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "tracker.db")

def get_connection():
    """
    Creates and returns a new SQLite database connection.
    Each thread / request creates its own connection for thread-safety.
    """
    return sqlite3.connect(DB_PATH)

# -----------------------------------------------------------------------------
# Section 2: Schema Initialization & Seed Data
# -----------------------------------------------------------------------------
def init_db():
    """
    Creates all required tables if they do not already exist,
    and seeds initial developer/distraction keywords if table is empty.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Activity Log: Records every window focus transition
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_title TEXT,
            app_name TEXT,
            category TEXT,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            is_split_screen BOOLEAN
        )
    ''')
    
    # 2. Idle Log: Records periods where user was away from keyboard/mouse
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idle_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            duration REAL
        )
    ''')
    
    # 3. Tasks: Daily task checklist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT,
            planned_date TEXT,
            status TEXT DEFAULT 'pending',
            start_time TEXT,
            completion_time TEXT,
            time_spent REAL DEFAULT 0.0
        )
    ''')
    
    # 4. Breaks: User rest periods
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            planned_end_time TEXT,
            actual_end_time TEXT,
            duration REAL
        )
    ''')
    
    # 5. Keywords: Training corpus for Naive Bayes classifier
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword_phrase TEXT UNIQUE,
            category TEXT,
            added_by_user BOOLEAN
        )
    ''')
    
    # 6. Daily Summary: Pre-aggregated metrics per calendar day
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_active_time REAL DEFAULT 0.0,
            total_distraction_time REAL DEFAULT 0.0,
            total_idle_time REAL DEFAULT 0.0,
            total_break_time REAL DEFAULT 0.0,
            tasks_completed INTEGER DEFAULT 0,
            tasks_planned INTEGER DEFAULT 0
        )
    ''')
    
    # 7. Classification Feedback: Human-in-the-loop retraining history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classification_feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER,
            predicted_label TEXT,
            user_label TEXT,
            confidence REAL,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    
    # Seed default keywords if database is new / empty
    cursor.execute('SELECT COUNT(*) FROM keywords')
    if cursor.fetchone()[0] == 0:
        initial_keywords = [
            # Intended Task keywords (Software engineering & research)
            ('vscode', 'Intended Task', 0),
            ('pycharm', 'Intended Task', 0),
            ('github', 'Intended Task', 0),
            ('stackoverflow', 'Intended Task', 0),
            ('terminal', 'Intended Task', 0),
            ('documentation', 'Intended Task', 0),
            ('jupyter', 'Intended Task', 0),
            ('colab', 'Intended Task', 0),
            ('aws', 'Intended Task', 0),
            ('gcp', 'Intended Task', 0),
            ('python', 'Intended Task', 0),
            ('keras', 'Intended Task', 0),
            ('pytorch', 'Intended Task', 0),
            
            # Distraction keywords (Entertainment & social media)
            ('youtube', 'Distraction', 0),
            ('instagram', 'Distraction', 0),
            ('facebook', 'Distraction', 0),
            ('reddit', 'Distraction', 0),
            ('netflix', 'Distraction', 0),
            ('twitter', 'Distraction', 0),
            ('tiktok', 'Distraction', 0),
            ('hulu', 'Distraction', 0),
            ('twitch', 'Distraction', 0)
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO keywords (keyword_phrase, category, added_by_user)
            VALUES (?, ?, ?)
        ''', initial_keywords)
        conn.commit()
        
    conn.close()

# -----------------------------------------------------------------------------
# Section 3: Keyword Operations (Classifier Training Dictionary)
# -----------------------------------------------------------------------------
def add_keyword(phrase: str, category: str, by_user: bool = True):
    """
    Inserts or updates a keyword phrase and its designated classification.
    
    :param phrase: Keyword or application name string (e.g. 'vscode', 'youtube').
    :param category: Target label ('Intended Task' or 'Distraction').
    :param by_user: Flag indicating whether added by user action (True) or system default (False).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO keywords (keyword_phrase, category, added_by_user)
            VALUES (?, ?, ?)
        ''', (phrase.lower().strip(), category, by_user))
        conn.commit()
    except sqlite3.IntegrityError:
        # Update existing record if phrase already exists
        cursor.execute('''
            UPDATE keywords SET category = ?, added_by_user = ? WHERE keyword_phrase = ?
        ''', (category, by_user, phrase.lower().strip()))
        conn.commit()
    finally:
        conn.close()

def get_keywords():
    """
    Retrieves all keywords as simple (phrase, category) tuples for model training.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword_phrase, category FROM keywords')
    results = cursor.fetchall()
    conn.close()
    return results

def get_keywords_detailed():
    """
    Retrieves all keywords with IDs and user-origin flags for the frontend management table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, keyword_phrase, category, added_by_user FROM keywords ORDER BY id DESC')
    results = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'phrase': r[1], 'category': r[2], 'added_by_user': bool(r[3])} for r in results]

def delete_keyword(keyword_id: int):
    """
    Removes a training keyword from the database by its primary key ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM keywords WHERE id = ?', (keyword_id,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Section 4: Activity Logging & Human Feedback Reclassification
# -----------------------------------------------------------------------------
def log_activity(window_title: str, app_name: str, category: str, start_time: str, end_time: str, duration: float, is_split_screen: bool) -> int:
    """
    Records a completed window focus session into the activity_log table.
    
    :returns: Primary key ID of the inserted activity log record.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log (window_title, app_name, category, start_time, end_time, duration, is_split_screen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (window_title, app_name, category, start_time, end_time, duration, is_split_screen))
    activity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return activity_id

def log_feedback(activity_id: int, predicted_label: str, user_label: str, confidence: float = 1.0):
    """
    Audits human correction of a model prediction into the classification_feedback table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO classification_feedback (activity_id, predicted_label, user_label, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (activity_id, predicted_label, user_label, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_activity_category(activity_id: int, new_category: str):
    """
    Reclassifies an existing logged activity based on user feedback.
    
    Side Effects:
      1. Updates the activity record in `activity_log`.
      2. Logs feedback into `classification_feedback`.
      3. Adds the window title as an explicit keyword in `keywords` table.
      4. Recalculates `daily_summary` totals for that calendar day.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT window_title, category, duration, start_time FROM activity_log WHERE id = ?', (activity_id,))
    row = cursor.fetchone()
    if row:
        title, old_cat, duration, start_time = row
        cursor.execute('UPDATE activity_log SET category = ? WHERE id = ?', (new_category, activity_id))
        conn.commit()
        
        # 1. Audit user feedback
        log_feedback(activity_id, old_cat, new_category, 1.0)
        
        # 2. Add keyword for this title to reinforce future ML training
        add_keyword(title.lower()[:50], new_category, by_user=True)
        
        # 3. Recalculate daily aggregate metrics
        day_str = start_time.split("T")[0] if "T" in start_time else datetime.now().strftime("%Y-%m-%d")
        recalculate_daily_summary(day_str)
    conn.close()

def recalculate_daily_summary(date_str: str):
    """
    Recomputes total active time and distraction time for a date by summing activity logs.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            SUM(duration),
            SUM(CASE WHEN category = 'Distraction' THEN duration ELSE 0 END)
        FROM activity_log
        WHERE start_time LIKE ?
    ''', (f"{date_str}%",))
    row = cursor.fetchone()
    total_active = (row[0] or 0.0)
    total_distraction = (row[1] or 0.0)

    cursor.execute('''
        INSERT INTO daily_summary (date, total_active_time, total_distraction_time)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_active_time = excluded.total_active_time,
            total_distraction_time = excluded.total_distraction_time
    ''', (date_str, total_active, total_distraction))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Section 5: Task Management Operations
# -----------------------------------------------------------------------------
def add_task(task_name: str, date_str: str) -> int:
    """
    Adds a new task item to the daily checklist.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (task_name, planned_date, status, start_time, completion_time, time_spent)
        VALUES (?, ?, 'pending', '', '', 0.0)
    ''', (task_name, date_str))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_tasks(date_str: str):
    """
    Fetches all tasks created for the specified calendar day.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, task_name, status, time_spent, completion_time FROM tasks WHERE planned_date = ? ORDER BY id DESC', (date_str,))
    results = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'task_name': r[1], 'status': r[2], 'time_spent': r[3], 'completion_time': r[4]} for r in results]

def update_task_status(task_id: int, status: str):
    """
    Toggles a task between 'pending' and 'complete', stamping completion timestamp.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET status = ?, completion_time = ? WHERE id = ?', 
                   (status, datetime.now().isoformat() if status == 'complete' else '', task_id))
    conn.commit()
    conn.close()

def delete_task(task_id: int):
    """
    Deletes a task by ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Section 6: Query Analytics & Summary Reporting
# -----------------------------------------------------------------------------
def get_recent_activities(limit: int = 50):
    """
    Retrieves the most recent activity log entries ordered by recency.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, window_title, app_name, category, duration, start_time, is_split_screen 
        FROM activity_log 
        ORDER BY id DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return [{
        'id': r[0],
        'window_title': r[1],
        'app_name': r[2],
        'category': r[3],
        'duration': r[4],
        'start_time': r[5],
        'is_split_screen': bool(r[6])
    } for r in results]

def get_daily_summary(date_str: str):
    """
    Returns aggregated metrics for date_str, including:
      - Productive Time = total_active_time - total_distraction_time
      - Focus Score (%) = (productive_time / total_active_time) * 100
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT total_active_time, total_distraction_time, total_idle_time, tasks_completed, tasks_planned FROM daily_summary WHERE date = ?', (date_str,))
    row = cursor.fetchone()
    conn.close()
    if row:
        active = row[0] or 0.0
        distraction = row[1] or 0.0
        idle = row[2] or 0.0
        productive = max(0.0, active - distraction)
        score = (productive / active * 100.0) if active > 0 else 100.0
        return {
            'date': date_str,
            'total_active_time': active,
            'total_distraction_time': distraction,
            'productive_time': productive,
            'total_idle_time': idle,
            'focus_score': round(score, 1),
            'tasks_completed': row[3],
            'tasks_planned': row[4]
        }
    return {
        'date': date_str,
        'total_active_time': 0.0,
        'total_distraction_time': 0.0,
        'productive_time': 0.0,
        'total_idle_time': 0.0,
        'focus_score': 100.0,
        'tasks_completed': 0,
        'tasks_planned': 0
    }

def get_hourly_breakdown(date_str: str):
    """
    Aggregates productive vs. distraction seconds into 24 one-hour bins (00:00 to 23:00)
    for rendering the 24-Hour Timeline Bar Chart.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            strftime('%H', start_time) as hour,
            category,
            SUM(duration) as total_sec
        FROM activity_log
        WHERE start_time LIKE ?
        GROUP BY hour, category
    ''', (f"{date_str}%",))
    rows = cursor.fetchall()
    conn.close()

    # Pre-populate all 24 hours of the day
    hourly = {f"{h:02d}": {"productive": 0.0, "distraction": 0.0} for h in range(24)}
    for r in rows:
        hour_str = r[0]
        cat = r[1]
        dur = r[2] or 0.0
        if hour_str in hourly:
            if cat == "Intended Task":
                hourly[hour_str]["productive"] += dur
            elif cat == "Distraction":
                hourly[hour_str]["distraction"] += dur
    return hourly

def reset_today_data(date_str: str):
    """
    Clears activity logs and resets the daily metrics record for the given date.
    Used when user clicks 'Reset Day' in the web interface.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM activity_log WHERE start_time LIKE ?', (f"{date_str}%",))
    cursor.execute('DELETE FROM daily_summary WHERE date = ?', (date_str,))
    cursor.execute('''
        INSERT INTO daily_summary (date, total_active_time, total_distraction_time, total_idle_time)
        VALUES (?, 0.0, 0.0, 0.0)
    ''', (date_str,))
    conn.commit()
    conn.close()

# -----------------------------------------------------------------------------
# Direct Execution Initialization
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
