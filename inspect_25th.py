
import sqlite3
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())
from app.data.core.database import get_db_path

def inspect_data(date_str):
    db_path = get_db_path()
    print(f"Checking data for {date_str} in {db_path}...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Check daily_stats
    print(f"\n[1] Checking daily_stats for {date_str}:")
    cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date_str,))
    row = cursor.fetchone()
    if row:
        print(f"  Found record for date: {row['date']}")
        print(f"  total_focus_time: {row['total_focus_time']} seconds ({row['total_focus_time']/3600:.2f} hours)")
        print(f"  total_entertainment_time: {row['total_entertainment_time']} seconds ({row['total_entertainment_time']/3600:.2f} hours)")
    else:
        print("  No record found in daily_stats.")

    # 2. Check window_sessions aggregation
    print(f"\n[2] Checking window_sessions aggregation for {date_str}:")
    start_ts = f"{date_str} 00:00:00"
    end_ts = f"{date_str} 23:59:59"
    
    # Total Focus (work + focus)
    cursor.execute("""
        SELECT SUM(duration) as total_seconds
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ? 
        AND status IN ('work', 'focus')
    """, (start_ts, end_ts))
    
    res = cursor.fetchone()
    raw_focus = res['total_seconds'] or 0
    print(f"  Calculated raw focus duration: {raw_focus} seconds ({raw_focus/3600:.2f} hours)")

    # 3. Check for potential issues (e.g. large ignored sessions or misclassified)
    print(f"\n[3] Checking top 5 longest sessions on {date_str}:")
    cursor.execute("""
        SELECT process_name, window_title, duration, status, start_time
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ?
        ORDER BY duration DESC
        LIMIT 5
    """, (start_ts, end_ts))
    
    for r in cursor.fetchall():
        print(f"  [{r['status']}] {r['process_name']} - {r['window_title']} ({r['duration']}s / {r['duration']/60:.1f}m)")

    conn.close()

if __name__ == "__main__":
    inspect_data('2026-01-25')
