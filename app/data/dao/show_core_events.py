import sys
import os
import sqlite3
from datetime import date

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
sys.path.insert(0, project_root)

from app.data.core.database import get_db_connection, get_core_events_db_connection

def show_today_core_events():
    today_str = date.today().strftime('%Y-%m-%d')
    print(f"Fetching Core Events for today ({today_str})...")
    
    with get_core_events_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM core_events WHERE date = ? ORDER BY category, rank",
            (today_str,)
        ).fetchall()
        
        if not rows:
            print("No Core Events found for today.")
            return

        print(f"{'Category':<15} | {'Rank':<5} | {'App':<20} | {'Duration (min)':<15} | {'Title'}")
        print("-" * 100)
        
        for row in rows:
            duration_min = round(row['total_duration'] / 60, 1)
            print(f"{row['category']:<15} | {row['rank']:<5} | {row['app_name']:<20} | {duration_min:<15} | {row['clean_title']}")

if __name__ == "__main__":
    show_today_core_events()
