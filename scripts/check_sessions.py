import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'focus_app.db')

def check_recent_sessions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n✅ [window_sessions] 最近 10 条记录:")
    cursor.execute("""
        SELECT * FROM window_sessions 
        ORDER BY id DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row['id']} | Date: {row['start_time']} | Dur: {row['duration']} | Status: {row['status']} | Title: {row['window_title'][:20]}")

    conn.close()

if __name__ == "__main__":
    check_recent_sessions()
