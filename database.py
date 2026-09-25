import sqlite3
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "tracker.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Activity Log
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
    
    # Idle Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS idle_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            end_time TEXT,
            duration REAL
        )
    ''')
    
    # Tasks
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
    
    # Breaks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            planned_end_time TEXT,
            actual_end_time TEXT,
            duration REAL
        )
    ''')
    
    # Keywords
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword_phrase TEXT UNIQUE,
            category TEXT,
            added_by_user BOOLEAN
        )
    ''')
    
    # Daily Summary
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
    
    # Classification Feedback
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
    
    # Pre-populate some keywords if the table is empty
    cursor.execute('SELECT COUNT(*) FROM keywords')
    if cursor.fetchone()[0] == 0:
        initial_keywords = [
            # Intended Task keywords (AI / Software Engineering context)
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
            
            # Distraction keywords
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

# Example wrapper functions for common operations
def add_keyword(phrase, category, by_user=True):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO keywords (keyword_phrase, category, added_by_user)
            VALUES (?, ?, ?)
        ''', (phrase.lower().strip(), category, by_user))
        conn.commit()
    except sqlite3.IntegrityError:
        cursor.execute('''
            UPDATE keywords SET category = ?, added_by_user = ? WHERE keyword_phrase = ?
        ''', (category, by_user, phrase.lower().strip()))
        conn.commit()
    finally:
        conn.close()

def get_keywords():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword_phrase, category FROM keywords')
    results = cursor.fetchall()
    conn.close()
    return results

def get_keywords_detailed():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, keyword_phrase, category, added_by_user FROM keywords ORDER BY id DESC')
    results = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'phrase': r[1], 'category': r[2], 'added_by_user': bool(r[3])} for r in results]

def delete_keyword(keyword_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM keywords WHERE id = ?', (keyword_id,))
    conn.commit()
    conn.close()

def log_activity(window_title, app_name, category, start_time, end_time, duration, is_split_screen):
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

def log_feedback(activity_id, predicted_label, user_label, confidence=1.0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO classification_feedback (activity_id, predicted_label, user_label, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (activity_id, predicted_label, user_label, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_activity_category(activity_id, new_category):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT window_title, category, duration, start_time FROM activity_log WHERE id = ?', (activity_id,))
    row = cursor.fetchone()
    if row:
        title, old_cat, duration, start_time = row
        cursor.execute('UPDATE activity_log SET category = ? WHERE id = ?', (new_category, activity_id))
        conn.commit()
        # Log feedback
        log_feedback(activity_id, old_cat, new_category, 1.0)
        # Add keyword for this title to help future classifications
        add_keyword(title.lower()[:50], new_category, by_user=True)
        
        # Adjust daily summary
        day_str = start_time.split("T")[0] if "T" in start_time else datetime.now().strftime("%Y-%m-%d")
        recalculate_daily_summary(day_str)
    conn.close()

def recalculate_daily_summary(date_str):
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

def add_task(task_name, date_str):
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

def get_tasks(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, task_name, status, time_spent, completion_time FROM tasks WHERE planned_date = ? ORDER BY id DESC', (date_str,))
    results = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'task_name': r[1], 'status': r[2], 'time_spent': r[3], 'completion_time': r[4]} for r in results]

def update_task_status(task_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET status = ?, completion_time = ? WHERE id = ?', 
                   (status, datetime.now().isoformat() if status == 'complete' else '', task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def get_recent_activities(limit=50):
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

def get_daily_summary(date_str):
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

def get_hourly_breakdown(date_str):
    """Returns productive and distraction duration per hour (00 to 23) for date_str."""
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

def reset_today_data(date_str):
    """Clears all activity logs and resets daily summary for the specified date."""
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

if __name__ == "__main__":
    init_db()
