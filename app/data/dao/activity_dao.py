import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.getcwd(), 'data', 'xiaoliu.db')

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_activity_logs_db():
    # Create activity_logs table and index, enforce protocol structure
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,   -- float type Unix timestamp
            status TEXT NOT NULL,      -- "focus"|"entertainment"|"idle"|"distracted"
            duration INTEGER NOT NULL  -- duration in seconds
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_logs(timestamp)')
    conn.commit()
    conn.close()

def insert_activity_log(status: str, timestamp: float, duration: int):
    # Insert an activity_logs record
    assert status in {"focus", "entertainment", "idle", "distracted"}
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO activity_logs (status, timestamp, duration) VALUES (?, ?, ?)",
        (status, timestamp, duration)
    )
    conn.commit()
    conn.close()

def fetch_latest_activity() -> Optional[dict]:
    # Fetch the latest record for /api/status/current
    conn = _get_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, status, timestamp, duration FROM activity_logs ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "status": row[1],
        "timestamp": row[2],
        "duration": row[3]
    }

def fetch_logs_by_date(date_str: str) -> list:
    # Fetch all segments for one day, used for daily report aggregation. date_str like '2026-01-14'
    start_ts = _date_str_to_ts(date_str)
    end_ts = start_ts + 86400
    conn = _get_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT status, timestamp, duration FROM activity_logs WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
        (start_ts, end_ts)
    ).fetchall()
    conn.close()
    return [
        {"status": r[0], "timestamp": r[1], "duration": r[2]}
        for r in rows
    ]

def _date_str_to_ts(date_str: str) -> int:
    # "2026-01-14" -> 1705171200 (midnight)
    import time, datetime
    y, m, d = map(int, date_str.split('-'))
    return int(time.mktime(datetime.datetime(y, m, d, 0, 0, 0).timetuple()))

class OcrDAO:
    # OCR record data access object
    @staticmethod
    def insert_record(content: str, app_name: str, screenshot_path: str = None):
        with _get_conn() as conn:
            conn.execute(
                'INSERT INTO ocr_records (content, app_name, screenshot_path) VALUES (?, ?, ?)',
                (content, app_name, screenshot_path)
            )
            conn.commit()

    @staticmethod
    def get_recent_records(limit=50):
        # Get recent OCR/screenshot records
        with _get_conn() as conn:
            rows = conn.execute(
                'SELECT id, timestamp, app_name, window_title, content FROM ocr_records ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            ).fetchall()
            if rows:
                # Try to build key->value dicts even if records exist
                cursor = conn.execute(
                    'SELECT id, timestamp, app_name, window_title, content FROM ocr_records LIMIT 1'
                )
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                return []