# -*- coding: utf-8 -*-
from app.data.core.database import get_db_connection
from datetime import datetime, timedelta

class AnalysisDAO:
    """数据分析与报表生成 DAO"""

    @staticmethod
    def get_focus_time_stats(start_date, end_date):
        """获取周期内的专注时长统计"""
        # Note: Aggregated sessions table is deleted, we need to calculate from window_sessions
        # start_date 和 end_date 是字符串 "YYYY-MM-DD"
        start_ts = f"{start_date} 00:00:00"
        end_ts = f"{end_date} 23:59:59"
        
        with get_db_connection() as conn:
            # 计算总时长 (所有记录)
            total_duration = conn.execute('''
                SELECT SUM(duration) FROM window_sessions 
                WHERE start_time BETWEEN ? AND ?
            ''', (start_ts, end_ts)).fetchone()[0] or 0
            
            # 计算专注时长 (status='work' or 'focus')
            focus_duration = conn.execute('''
                SELECT SUM(duration) FROM window_sessions 
                WHERE start_time BETWEEN ? AND ? 
                AND status IN ('work', 'focus')
            ''', (start_ts, end_ts)).fetchone()[0] or 0
            
            return {
                "total_seconds": total_duration,
                "focus_seconds": focus_duration,
                "focus_ratio": (focus_duration / total_duration) if total_duration > 0 else 0
            }

    @staticmethod
    def get_willpower_victories(start_date, end_date):
        """
        计算意志力胜利次数
        定义：Focus(>5min) -> Distraction(<5min) -> Focus(>5min)
        使用 window_sessions 表
        """
        start_ts = f"{start_date} 00:00:00"
        end_ts = f"{end_date} 23:59:59"
        
        with get_db_connection() as conn:
            # 按时间顺序拉取所有会话
            rows = conn.execute('''
                SELECT status, duration, start_time, process_name 
                FROM window_sessions
                WHERE start_time BETWEEN ? AND ?
                ORDER BY start_time ASC
            ''', (start_ts, end_ts)).fetchall()
            
            if not rows:
                return 0
                
            victories = 0
            state = 0
            
            for row in rows:
                status = row['status']
                duration = row['duration']
                
                is_focus = status in ['work', 'focus']
                is_distraction = status in ['entertainment', 'other', 'unknown']
                
                if state == 0:
                    if is_focus and duration > 300: # 5分钟以上
                        state = 1
                elif state == 1:
                    if is_distraction:
                        if duration < 300: # 5分钟以内的短途走神
                            state = 2
                        else:
                            state = 0 
                    elif is_focus:
                        pass
                elif state == 2:
                    if is_focus:
                        victories += 1
                        state = 1 if duration > 300 else 0
                    elif is_distraction:
                        state = 0

            return victories

    @staticmethod
    def get_daily_breakdown(start_date, end_date):
        """获取每日详情：Top Activity, Total Time, Max Streak"""
        # Since aggregated_sessions is gone, we need to calculate metrics from window_sessions
        # This might be less accurate for 'Max Streak' without merging, but it's a trade-off.
        # We can implement a simple in-memory merge if needed, but for now let's query raw.
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        results = []
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            day_start = f"{date_str} 00:00:00"
            day_end = f"{date_str} 23:59:59"
            
            with get_db_connection() as conn:
                # 1. 当日总投入时长 (Focus)
                day_focus_seconds = conn.execute('''
                    SELECT SUM(duration) FROM window_sessions 
                    WHERE start_time BETWEEN ? AND ? 
                    AND status IN ('work', 'focus')
                ''', (day_start, day_end)).fetchone()[0] or 0
                
                # 2. 最长持续 (Max Streak) - Approximation from raw sessions
                # ideally we should merge adjacent work sessions first
                # Let's do a simple in-memory merge for max streak calculation
                rows = conn.execute('''
                    SELECT duration, status FROM window_sessions
                    WHERE start_time BETWEEN ? AND ?
                    ORDER BY start_time ASC
                ''', (day_start, day_end)).fetchall()
                
                max_streak_seconds = 0
                current_streak = 0
                for r in rows:
                    if r['status'] in ['work', 'focus']:
                        current_streak += r['duration']
                    else:
                        max_streak_seconds = max(max_streak_seconds, current_streak)
                        current_streak = 0
                max_streak_seconds = max(max_streak_seconds, current_streak)
                
                # 3. 核心事项 (Top Activity by Duration)
                # Group by window_title or process_name
                top_activity_row = conn.execute('''
                    SELECT window_title, SUM(duration) as total_dur FROM window_sessions 
                    WHERE start_time BETWEEN ? AND ? 
                    AND status IN ('work', 'focus')
                    GROUP BY window_title
                    ORDER BY total_dur DESC
                    LIMIT 1
                ''', (day_start, day_end)).fetchone()
                
                top_activity = top_activity_row['window_title'] if top_activity_row else "无记录"
                
                results.append({
                    "date": date_str,
                    "focus_hours": round(day_focus_seconds / 3600, 1),
                    "max_streak_minutes": int(max_streak_seconds / 60),
                    "top_activity_raw": top_activity
                })
            
            current_dt += timedelta(days=1)
            
        return results

    @staticmethod
    def get_best_day(daily_breakdown):
        """从每日数据中找出最佳日"""
        if not daily_breakdown:
            return None
        return max(daily_breakdown, key=lambda x: x['focus_hours'])

    @staticmethod
    def get_top_apps(start_date, end_date, limit=3):
        """获取主要阵地 (App 使用时长排名)"""
        start_ts = f"{start_date} 00:00:00"
        end_ts = f"{end_date} 23:59:59"
        
        with get_db_connection() as conn:
            rows = conn.execute('''
                SELECT process_name, SUM(duration) as total_duration
                FROM window_sessions
                WHERE start_time BETWEEN ? AND ?
                AND status IN ('work', 'focus')
                GROUP BY process_name
                ORDER BY total_duration DESC
                LIMIT ?
            ''', (start_ts, end_ts, limit)).fetchall()
            
            return [{"app": row['process_name'], "duration": row['total_duration']} for row in rows]
