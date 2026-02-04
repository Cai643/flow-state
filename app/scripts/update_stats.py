
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.data.dao.stats_calculator import calculate_period_stats

def update_recent_stats():
    print("Updating period stats for the last 7 days...")
    today = datetime.now().date()
    
    for i in range(7):
        target_date = today - timedelta(days=i)
        d_str = target_date.strftime("%Y-%m-%d")
        calculate_period_stats(d_str)
        
    print("Update complete.")

if __name__ == "__main__":
    update_recent_stats()
