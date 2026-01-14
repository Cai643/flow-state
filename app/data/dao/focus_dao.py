import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), 'data', 'xiaoliu.db')

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_focus_db():
    conn = _get_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS focus_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status_code INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER NOT NULL      -- 单位秒
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(status_code: int, timestamp: str, freq_sec=5):
    """
    智能合并插入日志。和“实时合并”思路一样。
    - 重复状态合并到前一行，duration累加
    - 切换状态，新起一行
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status_code, start_time, duration FROM focus_record ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    ts_now = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

    if last and last[1] == status_code:
        # 状态未变化，直接累加duration
        last_id, _, start_str, last_dur = last
        cursor.execute("UPDATE focus_record SET duration=? WHERE id=?",
                       (last_dur + freq_sec, last_id))
    else:
        # 状态变化，插入新行（开始时间就是本条的timestamp，duration为freq_sec）
        cursor.execute("INSERT INTO focus_record (status_code, start_time, duration) VALUES (?, ?, ?)",
                       (status_code, timestamp, freq_sec))
    conn.commit()
    conn.close()

def fetch_records_by_date(date_str: str):
    """
    返回指定日期的所有纪录（原始/合并后），按起始时间排序
    :param date_str: "2026-01-14"
    :return: [(status_code, start_time, duration), ...]
    """
    conn = _get_conn()
    cursor = conn.execute(
        "SELECT status_code, start_time, duration FROM focus_record WHERE start_time LIKE ? ORDER BY start_time",
        (f"{date_str}%",)
    )
    out = cursor.fetchall()
    conn.close()
    return out

def clear_all_data_for_dev():  # 调试专用
    conn = _get_conn()
    conn.execute("DELETE FROM focus_record")
    conn.commit()
    conn.close()