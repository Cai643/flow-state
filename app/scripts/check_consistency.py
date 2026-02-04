import sqlite3
import os
import sys
from datetime import date

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.data.core.database import DB_PATH

def check_consistency():
    if not os.path.exists(DB_PATH):
        print(f"❌ 错误: 找不到数据库文件: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    target_date = '2026-01-25' # 检查今天的日期
    print(f"📊 正在检查数据一致性: {target_date}\n")

    # 1. 查询 daily_stats (统计表)
    cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (target_date,))
    daily_row = cursor.fetchone()
    
    if daily_row:
        daily_max_streak = daily_row['max_focus_streak']
        daily_mins = round(daily_max_streak / 60, 1)
        print(f"✅ [daily_stats] 记录:")
        print(f"   Total Focus: {daily_row['total_focus_time']}s ({round(daily_row['total_focus_time']/60, 1)}m)")
        print(f"   Max Streak: {daily_max_streak}s ({daily_mins}m)")
        print(f"   Efficiency: {daily_row['efficiency_score']}")
    else:
        print("❌ daily_stats 中没有今日数据")

    # 2. 查询 window_sessions (明细表) - 单个窗口最长持续时间
    cursor.execute("""
        SELECT MAX(duration) as max_dur 
        FROM window_sessions 
        WHERE date(start_time) = ? AND status IN ('focus', 'work')
    """, (target_date,))
    session_row = cursor.fetchone()
    
    session_max_dur = session_row['max_dur'] if session_row and session_row['max_dur'] else 0
    session_mins = round(session_max_dur / 60, 1)
    
    print(f"\n✅ [window_sessions] 单个窗口最大持续时间 (MAX duration):")
    print(f"   -> {session_max_dur} 秒 ({session_mins} 分钟)")
    
    # 3. 查询 window_sessions 前 10 条长记录
    print("\n✅ [window_sessions] 今日最长 Top 10 Focus 记录:")
    cursor.execute("""
        SELECT start_time, duration, process_name, window_title 
        FROM window_sessions 
        WHERE date(start_time) = ? AND status IN ('focus', 'work')
        ORDER BY duration DESC
        LIMIT 10
    """, (target_date,))
    rows = cursor.fetchall()
    for row in rows:
        print(f"   {row['start_time']} | {round(row['duration']/60, 1)}m | {row['process_name']} | {row['window_title'][:30]}")

    conn.close()

if __name__ == "__main__":
    check_consistency()
