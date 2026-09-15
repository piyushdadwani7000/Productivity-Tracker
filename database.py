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
        ''', (phrase.lower(), category, by_user))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    finally:
        conn.close()

def get_keywords():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT keyword_phrase, category FROM keywords')
    results = cursor.fetchall()
    conn.close()
    return results

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

def log_feedback(activity_id, predicted_label, user_label, confidence):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO classification_feedback (activity_id, predicted_label, user_label, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (activity_id, predicted_label, user_label, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_task(task_name, date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks (task_name, planned_date, status, start_time, completion_time, time_spent)
        VALUES (?, ?, 'pending', '', '', 0.0)
    ''', (task_name, date_str))
    conn.commit()
    conn.close()

def get_tasks(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, task_name, status, time_spent FROM tasks WHERE planned_date = ?', (date_str,))
    results = cursor.fetchall()
    conn.close()
    return results

def update_task_status(task_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET status = ?, completion_time = ? WHERE id = ?', 
                   (status, datetime.now().isoformat() if status == 'complete' else '', task_id))
    conn.commit()
    conn.close()

def get_recent_activities(limit=15):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, window_title, app_name, category, duration, start_time 
        FROM activity_log 
        ORDER BY id DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    init_db()
