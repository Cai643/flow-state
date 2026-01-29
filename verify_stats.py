
import sys
import os
from datetime import date

# Add project root to path
sys.path.insert(0, os.getcwd())

try:
    from app.data.dao.activity_dao import StatsDAO
    print(f"StatsDAO loaded from: {sys.modules['app.data.dao.activity_dao'].__file__}")
    
    if hasattr(StatsDAO, 'get_daily_summary'):
        print("Success: StatsDAO has get_daily_summary method.")
        summary = StatsDAO.get_daily_summary(date.today())
        print(f"Summary for today: {summary}")
    else:
        print("Failure: StatsDAO does NOT have get_daily_summary method.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
