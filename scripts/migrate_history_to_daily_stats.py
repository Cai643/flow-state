import sys
import os
import sqlite3
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.core.database import get_db_connection

def migrate_history():
    """
    从 window_sessions 聚合历史数据，并回填到 daily_stats 表中。
    解决 daily_stats 作为新表缺少历史数据的问题。
    """
    print("Starting migration: window_sessions -> daily_stats...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 聚合查询：按天分组，计算 focus, entertainment 总时长和最大连续时长
        # 注意：这里按 date(start_time) 分组，忽略跨天微小误差
        cursor.execute('''
            SELECT 
                date(start_time) as day,
                SUM(CASE WHEN status IN ('work', 'focus') THEN duration ELSE 0 END) as focus_time,
                SUM(CASE WHEN status = 'entertainment' THEN duration ELSE 0 END) as ent_time,
                MAX(CASE WHEN status IN ('work', 'focus') THEN duration ELSE 0 END) as max_streak_raw
            FROM window_sessions
            GROUP BY date(start_time)
            ORDER BY day DESC
        ''')
        
        rows = cursor.fetchall()
        
        for row in rows:
            day = row['day']
            f_time = row['focus_time'] or 0
            e_time = row['ent_time'] or 0
            streak = row['max_streak_raw'] or 0 # 这里只能拿到单次最大，无法合并，作为保底值
            
            # 简单的效能分计算
            total = f_time + e_time
            score = int((f_time / total * 100)) if total > 0 else 0
            
            print(f"Migrating {day}: Focus={f_time}s, Ent={e_time}s, Streak={streak}s")
            
            # 2. Upsert 到 daily_stats
            # 如果已存在（比如今天的实时数据），我们选择【覆盖】还是【累加】？
            # 考虑到 window_sessions 是全量历史，覆盖通常更安全，避免重复累加。
            # 但为了保险，我们可以只更新那些比当前值大的（比如历史数据）。
            # 这里采用：INSERT OR REPLACE 逻辑，完全信任 window_sessions 的聚合结果。
            
            cursor.execute('''
                INSERT INTO daily_stats (date, total_focus_time, total_entertainment_time, max_focus_streak, efficiency_score)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                total_focus_time = excluded.total_focus_time,
                total_entertainment_time = excluded.total_entertainment_time,
                max_focus_streak = MAX(daily_stats.max_focus_streak, excluded.max_focus_streak),
                efficiency_score = excluded.efficiency_score
            ''', (day, f_time, e_time, streak, score))
            
        conn.commit()
        print("Migration completed.")

if __name__ == "__main__":
    migrate_history()
