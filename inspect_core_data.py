
import sqlite3
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.getcwd())
from app.data.core.database import get_db_path

def inspect_core_tables():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"Database: {db_path}")
    
    # Calculate date range (last 5 days)
    today = datetime.now().date()
    start_date = today - timedelta(days=5)
    start_str = start_date.strftime("%Y-%m-%d")
    
    print(f"\n=== 5. Core Events Table (Since {start_str}) ===")
    cursor.execute("""
        SELECT date, category, rank, app_name, clean_title, total_duration, event_count
        FROM core_events
        WHERE date >= ?
        ORDER BY date DESC, category DESC, rank ASC
    """, (start_str,))
    
    current_date = None
    for row in cursor.fetchall():
        if row['date'] != current_date:
            current_date = row['date']
            print(f"\n--- {current_date} ---")
        
        dur_str = f"{row['total_duration']/60:.1f}m"
        if row['total_duration'] > 3600:
            dur_str = f"{row['total_duration']/3600:.1f}h"
            
        print(f"  [{row['category'].upper()}] #{row['rank']} {row['app_name']} - {row['clean_title']} ({dur_str})")

    print(f"\n=== 6. Period Stats Table (Since {start_str}) ===")
    cursor.execute("""
        SELECT date, total_focus, daily_summary, ai_insight
        FROM period_stats
        WHERE date >= ?
        ORDER BY date DESC
    """, (start_str,))
    
    for row in cursor.fetchall():
        focus_h = (row['total_focus'] or 0) / 3600
        print(f"\n--- {row['date']} ---")
        print(f"  Total Focus: {focus_h:.2f}h")
        print(f"  Daily Summary (AI): {row['daily_summary']}")
        # print(f"  AI Insight: {row['ai_insight']}")

    conn.close()

if __name__ == "__main__":
    inspect_core_tables()
