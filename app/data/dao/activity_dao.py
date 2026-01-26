# -*- coding: utf-8 -*-
from app.data.core.database import get_db_connection

from datetime import datetime

class ActivityDAO:
    """活动日志数据访问对象"""
    
    @staticmethod
    def insert_log(status: str, duration: int, timestamp=None, summary: str = None, raw_data: str = None):
        with get_db_connection() as conn:
            if timestamp:
                # 如果是 float/int 时间戳，转换为字符串
                if isinstance(timestamp, (float, int)):
                    ts_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ts_str = timestamp
                    
                conn.execute(
                    'INSERT INTO activity_logs (status, duration, timestamp, summary, raw_data) VALUES (?, ?, ?, ?, ?)',
                    (status, duration, ts_str, summary, raw_data)
                )
            else:
                conn.execute(
                    'INSERT INTO activity_logs (status, duration, summary, raw_data) VALUES (?, ?, ?, ?)',
                    (status, duration, summary, raw_data)
                )
            conn.commit()

    @staticmethod
    def get_latest_log():
        """获取最新的一条活动日志"""
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 1'
            ).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def get_logs_by_date(date_obj):
        """获取某日的所有活动日志"""
        start_time = f"{date_obj} 00:00:00"
        end_time = f"{date_obj} 23:59:59"
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM activity_logs WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC',
                (start_time, end_time)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_recent_activities(limit=50):
        """获取最近的活动记录"""
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]


class WindowSessionDAO:
    """窗口会话数据访问对象"""
    
    @staticmethod
    def get_last_session():
        """获取最后一条会话记录"""
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM window_sessions ORDER BY id DESC LIMIT 1'
            ).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def create_session(window_title, process_name, start_time, duration, status, summary):
        """创建新的会话记录"""
        with get_db_connection() as conn:
            # 确保时间格式统一
            if isinstance(start_time, (float, int)):
                start_ts = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
            else:
                start_ts = start_time
                
            # end_time 初始设为 start_time + duration (如果是实时流，可能duration很短)
            # 或者直接设为 start_time，后续 update 时更新 end_time
            # 这里我们计算出 end_time
            # 注意：start_time 是 float/int 还是 string? 上面已处理
            # 为了计算 end_time，我们需要 start_time 的数值
            
            # 简单起见，我们存储 start_time, end_time, duration
            # end_time = datetime.now()
            
            conn.execute(
                '''INSERT INTO window_sessions 
                   (window_title, process_name, start_time, end_time, duration, status, summary) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (window_title, process_name, start_ts, start_ts, duration, status, summary)
            )
            conn.commit()

    @staticmethod
    def update_session_duration(session_id, additional_duration):
        """更新会话时长和结束时间"""
        with get_db_connection() as conn:
            # 更新 duration 和 end_time
            # SQLite 的 datetime('now') 可以获取当前时间作为 end_time
            conn.execute(
                '''UPDATE window_sessions 
                   SET duration = duration + ?, 
                       end_time = datetime('now', 'localtime')
                   WHERE id = ?''',
                (additional_duration, session_id)
            )
            conn.commit()

    @staticmethod
    def update_session_summary(session_id, summary):
        """更新会话摘要"""
        with get_db_connection() as conn:
            conn.execute(
                '''UPDATE window_sessions 
                   SET summary = ? 
                   WHERE id = ?''',
                (summary, session_id)
            )
            conn.commit()

    @staticmethod
    def get_today_sessions():
        """获取今天的会话记录 (用于日报时间轴)"""
        from datetime import date
        today_str = date.today().strftime('%Y-%m-%d')
        start_time = f"{today_str} 00:00:00"
        
        with get_db_connection() as conn:
            # 按开始时间正序排列
            rows = conn.execute(
                'SELECT * FROM window_sessions WHERE start_time >= ? ORDER BY start_time ASC',
                (start_time,)
            ).fetchall()
            return [dict(row) for row in rows]

class StatsDAO:
    """统计数据访问对象"""
    
    @staticmethod
    def update_daily_stats(date_obj, status: str, duration: int, current_streak: int = 0, willpower_wins_increment: int = 0):
        """更新每日统计"""
        # 1. 累加时长
        col_name = None
        if status in ['focus', 'work']:
            col_name = "total_focus_time"
        elif status == 'entertainment':
            col_name = "total_entertainment_time"
            
        with get_db_connection() as conn:
            # 先尝试插入初始记录
            conn.execute('''
                INSERT OR IGNORE INTO daily_stats (date) VALUES (?)
            ''', (date_obj,))
            
            # 2. 更新累加字段
            if col_name:
                conn.execute(f'''
                    UPDATE daily_stats 
                    SET {col_name} = {col_name} + ?
                    WHERE date = ?
                ''', (duration, date_obj))
            
            # 3. 更新当前连续时长 (只在 focus/work 时更新，entertainment 时可能需要重置或保持)
            # 如果 status 是 focus/work，current_streak 应该是外部传入的当前累积值
            # 如果 status 是 entertainment，外部可能会传入 0
            conn.execute('''
                UPDATE daily_stats 
                SET current_focus_streak = ?
                WHERE date = ?
            ''', (current_streak, date_obj))
            
            # 4. 更新最大连续时长 (如果当前连续时长超过了历史最大值)
            # 只有在 focus/work 时才有可能打破记录
            if status in ['focus', 'work']:
                conn.execute('''
                    UPDATE daily_stats 
                    SET max_focus_streak = MAX(max_focus_streak, ?)
                    WHERE date = ?
                ''', (current_streak, date_obj))
            
            # 4.5 更新意志力胜利次数
            if willpower_wins_increment > 0:
                 conn.execute('''
                    UPDATE daily_stats 
                    SET willpower_wins = willpower_wins + ?
                    WHERE date = ?
                ''', (willpower_wins_increment, date_obj))
                
            # 5. 更新效能指数 (简单计算: focus / (focus + entertainment) * 100)
            # 这是一个简单的实时计算，也可以放在应用层算
            # 这里用 SQL 计算
            conn.execute('''
                UPDATE daily_stats 
                SET efficiency_score = CASE 
                WHEN (total_focus_time + total_entertainment_time) > 0 
                THEN (total_focus_time * 100 / (total_focus_time + total_entertainment_time))
                ELSE 0 
                END
                WHERE date = ?
            ''', (date_obj,))
            
            conn.commit()

    @staticmethod
    def get_daily_summary(date_obj):
        """获取某日的统计摘要"""
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM daily_stats WHERE date = ?', (date_obj,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def get_recent_stats(days=7):
        """获取最近N天的统计数据"""
        with get_db_connection() as conn:
            rows = conn.execute(
                f'SELECT * FROM daily_stats ORDER BY date DESC LIMIT ?',
                (days,)
            ).fetchall()
            return [dict(row) for row in rows]
