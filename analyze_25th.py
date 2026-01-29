
import sqlite3
import sys
import os

sys.path.append(os.getcwd())
from app.data.core.database import get_db_path

def analyze_25th_distribution():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    date_str = '2026-01-25'
    start_ts = f"{date_str} 00:00:00"
    end_ts = f"{date_str} 23:59:59"
    
    print(f"--- Analysis for {date_str} ---")
    
    # 1. Total Tracked Time
    cursor.execute("""
        SELECT SUM(duration) as total
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ?
    """, (start_ts, end_ts))
    total_tracked = cursor.fetchone()['total'] or 0
    print(f"Total Tracked Time: {total_tracked/3600:.2f} hours")
    
    # 2. Group by Status
    print("\n--- By Status ---")
    cursor.execute("""
        SELECT status, SUM(duration) as dur
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ?
        GROUP BY status
    """, (start_ts, end_ts))
    for r in cursor.fetchall():
        print(f"{r['status']}: {r['dur']/3600:.2f} hours")
        
    # 3. Top Entertainment Apps
    print("\n--- Top Entertainment Apps ---")
    cursor.execute("""
        SELECT process_name, SUM(duration) as dur
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ? AND status = 'entertainment'
        GROUP BY process_name
        ORDER BY dur DESC
        LIMIT 5
    """, (start_ts, end_ts))
    for r in cursor.fetchall():
        print(f"{r['process_name']}: {r['dur']/60:.1f} minutes")

    # 4. Top 'Unknown' or other Apps
    print("\n--- Top Other/Unknown Apps ---")
    cursor.execute("""
        SELECT process_name, SUM(duration) as dur
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ? AND status NOT IN ('focus', 'work', 'entertainment')
        GROUP BY process_name
        ORDER BY dur DESC
        LIMIT 5
    """, (start_ts, end_ts))
    for r in cursor.fetchall():
        print(f"{r['process_name']}: {r['dur']/60:.1f} minutes")

    conn.close()

if __name__ == "__main__":
    analyze_25th_distribution()
