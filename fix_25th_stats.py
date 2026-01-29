
import sqlite3
import sys
import os

sys.path.append(os.getcwd())
from app.data.core.database import get_db_path

def fix_and_recalc_25th():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    date_str = '2026-01-25'
    start_ts = f"{date_str} 00:00:00"
    end_ts = f"{date_str} 23:59:59"
    
    print(f"--- Fixing stats for {date_str} ---")
    
    # 1. Update Feishu to 'work'
    print("Updating Feishu.exe status to 'work'...")
    cursor.execute("""
        UPDATE window_sessions
        SET status = 'work'
        WHERE start_time BETWEEN ? AND ?
        AND process_name LIKE '%Feishu%'
        AND status = 'entertainment'
    """, (start_ts, end_ts))
    affected = cursor.rowcount
    print(f"Updated {affected} rows.")
    
    # 2. Recalculate totals
    print("Recalculating daily totals...")
    
    # Calculate Focus (work + focus)
    cursor.execute("""
        SELECT SUM(duration) as total
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ? 
        AND status IN ('work', 'focus')
    """, (start_ts, end_ts))
    new_focus = cursor.fetchone()['total'] or 0
    
    # Calculate Entertainment
    cursor.execute("""
        SELECT SUM(duration) as total
        FROM window_sessions 
        WHERE start_time BETWEEN ? AND ? 
        AND status = 'entertainment'
    """, (start_ts, end_ts))
    new_ent = cursor.fetchone()['total'] or 0
    
    print(f"New Focus: {new_focus}s ({new_focus/3600:.2f}h)")
    print(f"New Entertainment: {new_ent}s ({new_ent/3600:.2f}h)")
    
    # 3. Update daily_stats table
    # Check if record exists
    cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date_str,))
    if cursor.fetchone():
        print("Updating existing daily_stats record...")
        cursor.execute("""
            UPDATE daily_stats
            SET total_focus_time = ?,
                total_entertainment_time = ?
            WHERE date = ?
        """, (new_focus, new_ent, date_str))
    else:
        print("Creating new daily_stats record...")
        cursor.execute("""
            INSERT INTO daily_stats (date, total_focus_time, total_entertainment_time)
            VALUES (?, ?, ?)
        """, (date_str, new_focus, new_ent))
        
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    fix_and_recalc_25th()
