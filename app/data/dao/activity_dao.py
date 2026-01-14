import sqlite3
import os
from typing import Optional

DB_PATH = os.path.join(os.getcwd(), 'data', 'xiaoliu.db')

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_activity_logs_db():
    """创建 activity_logs 及索引，自动对齐协议表结构"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,   -- float型Unix时间戳
            status TEXT NOT NULL,      -- "focus"|"entertainment"|"idle"|"distracted"
            duration INTEGER NOT NULL  -- 单位为秒
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_logs(timestamp)')
    conn.commit()
    conn.close()

def insert_activity_log(status: str, timestamp: float, duration: int):
    """插入一条 activity_logs 记录"""
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
    """查最新一条，用于 /api/status/current。返回符合协议格式"""
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
    """查一天的所有段，用于日报聚合。date_str如'2026-01-14'"""
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
    # "2026-01-14" -> 1705171200 (零点)
    import time, datetime
    y, m, d = map(int, date_str.split('-'))
    return int(time.mktime(datetime.datetime(y, m, d, 0, 0, 0).timetuple()))

# --------- 以下保留主库新加的重要业务 ---------
class OcrDAO:
    """OCR 记录数据访问对象"""

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
        """获取最近的 OCR/截图记录"""
        with _get_conn() as conn:
            rows = conn.execute(
                'SELECT id, timestamp, app_name, window_title, content FROM ocr_records ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            ).fetchall()
            return [dict(zip([c[0] for c in rows.cursor_description], row)) for row in rows] if rows else []