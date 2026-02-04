
import sqlite3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.data.core.database import get_db_path

def check_and_fix_all_stats():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"Database: {db_path}")
    
    # --- Step 1: Global Misclassification Fix ---
    print("\n[1] Fixing global misclassifications...")
    # List of keywords/apps that should definitely be 'work'
    # 'WeChat' is tricky, often personal, so skipping it for auto-fix unless it's WeChatWork
    work_apps = [
        'Feishu', 'Lark', 'DingTalk', 'WeChatWork', # Communication
        'Teams', 'Zoom', 'Meeting', 'TencentMeeting', 'wemeetapp', # Meetings
        'Trae', 'Code', 'PyCharm', 'idea64', 'studio', 'sublime', 'notepad++', # Dev
        'Word', 'Excel', 'PowerPoint', 'WPS' # Office
    ]
    
    total_fixed = 0
    for app in work_apps:
        cursor.execute("""
            UPDATE window_sessions
            SET status = 'work'
            WHERE process_name LIKE ? 
            AND status IN ('entertainment', 'unknown', 'misc')
        """, (f'%{app}%',))
        if cursor.rowcount > 0:
            print(f"  - Fixed {cursor.rowcount} sessions for '{app}' -> 'work'")
            total_fixed += cursor.rowcount
            
    print(f"  Total sessions reclassified: {total_fixed}")

    # --- Step 2: Recalculate and Sync daily_stats ---
    print("\n[2] Checking consistency between 'window_sessions' and 'daily_stats'...")
    
    # Get all unique dates from window_sessions
    cursor.execute("""
        SELECT DISTINCT date(start_time) as d 
        FROM window_sessions 
        WHERE start_time IS NOT NULL 
        ORDER BY d
    """)
    dates = [row['d'] for row in cursor.fetchall() if row['d']]
    
    updated_days = 0
    
    for d in dates:
        start_ts = f"{d} 00:00:00"
        end_ts = f"{d} 23:59:59"
        
        # Calculate from raw data
        # Focus = work + focus
        cursor.execute("""
            SELECT SUM(duration) as total
            FROM window_sessions 
            WHERE start_time BETWEEN ? AND ? 
            AND status IN ('work', 'focus')
        """, (start_ts, end_ts))
        calc_focus = cursor.fetchone()['total'] or 0
        
        # Entertainment
        cursor.execute("""
            SELECT SUM(duration) as total
            FROM window_sessions 
            WHERE start_time BETWEEN ? AND ? 
            AND status = 'entertainment'
        """, (start_ts, end_ts))
        calc_ent = cursor.fetchone()['total'] or 0
        
        # Get stored stats
        cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (d,))
        stored = cursor.fetchone()
        
        stored_focus = stored['total_focus_time'] if stored else 0
        stored_ent = stored['total_entertainment_time'] if stored else 0
        
        # Check for discrepancy (allow small 60s diff)
        diff_focus = abs(calc_focus - stored_focus)
        diff_ent = abs(calc_ent - stored_ent)
        
        if diff_focus > 60 or diff_ent > 60 or not stored:
            print(f"  Mismatch found for {d}:")
            print(f"    Stored Focus: {stored_focus/3600:.2f}h | Calc Focus: {calc_focus/3600:.2f}h")
            print(f"    Stored Ent:   {stored_ent/3600:.2f}h | Calc Ent:   {calc_ent/3600:.2f}h")
            
            if stored:
                cursor.execute("""
                    UPDATE daily_stats
                    SET total_focus_time = ?,
                        total_entertainment_time = ?
                    WHERE date = ?
                """, (calc_focus, calc_ent, d))
            else:
                cursor.execute("""
                    INSERT INTO daily_stats (date, total_focus_time, total_entertainment_time)
                    VALUES (?, ?, ?)
                """, (d, calc_focus, calc_ent))
            
            updated_days += 1
            
    conn.commit()
    conn.close()
    
    print(f"\nDone. Sync complete for {len(dates)} days. Updated {updated_days} records.")

if __name__ == "__main__":
    check_and_fix_all_stats()
