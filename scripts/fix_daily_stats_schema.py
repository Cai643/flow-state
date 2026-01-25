import sys
import os
import sqlite3

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.core.database import get_db_connection

def fix_daily_stats():
    """
    将 daily_stats 表中废弃的 total_work_time 字段清零。
    解决旧数据叠加导致 UI 显示时长翻倍的问题。
    """
    print("Fixing daily_stats: Zeroing out deprecated 'total_work_time'...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 检查是否存在 total_work_time 列
        try:
            cursor.execute('SELECT total_work_time FROM daily_stats LIMIT 1')
            has_col = True
        except sqlite3.OperationalError:
            print("Column 'total_work_time' does not exist. No fix needed.")
            has_col = False
            
        if has_col:
            # 将所有记录的 total_work_time 设为 0
            cursor.execute('UPDATE daily_stats SET total_work_time = 0')
            conn.commit()
            print(f"Successfully reset total_work_time to 0 for {cursor.rowcount} rows.")
            
            # 验证
            cursor.execute('SELECT date, total_focus_time, total_work_time FROM daily_stats WHERE date = DATE("now", "localtime")')
            row = cursor.fetchone()
            if row:
                print(f"Verification (Today): Focus={row['total_focus_time']}s, Work={row['total_work_time']}s")
                print(f"UI Should Display: {round(row['total_focus_time']/3600, 2)}h")
        
if __name__ == "__main__":
    fix_daily_stats()
