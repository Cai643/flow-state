# -*- coding: utf-8 -*-
"""
[正在使用]
活动历史管理器 (业务逻辑层)
负责管理活动状态的流转和记录。
通过 DAO 层与数据库交互。
"""

import time
from datetime import date
from app.data import ActivityDAO, StatsDAO, OcrDAO

class ActivityHistoryManager:
    """活动历史管理器"""
    
    def __init__(self):
        self.current_status = None
        self.status_start_time = None
        # 内存缓存，用于快速 UI 展示
        self._history_cache = [] 
    
    def update(self, status: str):
        """更新当前状态"""
        current_time = time.time()
        
        # 首次运行
        if self.current_status is None:
            self.current_status = status
            self.status_start_time = current_time
            return

        # 状态改变，保存历史
        if status != self.current_status:
            duration_seconds = int(current_time - self.status_start_time)
            # 过滤短时抖动
            if duration_seconds > 2:
                self._save_record(self.current_status, duration_seconds)
                self._update_cache(self.current_status, int(duration_seconds / 60), self.status_start_time)
            
            self.current_status = status
            self.status_start_time = current_time
    
    def _save_record(self, status: str, duration: int):
        """调用 DAO 保存数据"""
        try:
            # 1. 写入流水日志
            ActivityDAO.insert_log(status, duration)
            
            # 2. 更新每日统计
            today = date.today()
            StatsDAO.update_daily_stats(today, status, duration)
                    
        except Exception as e:
            print(f"[HistoryManager] DB Error: {e}")

    def _update_cache(self, status, duration_mins, timestamp):
        self._history_cache.append({
            'status': status,
            'duration': duration_mins,
            'timestamp': timestamp
        })
        if len(self._history_cache) > 10:
            self._history_cache = self._history_cache[-10:]

    def add_ocr_record(self, content: str, app_name: str, screenshot_path: str = None):
        """添加 OCR 记录"""
        try:
            OcrDAO.insert_record(content, app_name, screenshot_path)
        except Exception as e:
            print(f"[HistoryManager] OCR DB Error: {e}")

    def get_current_duration(self) -> int:
        if self.status_start_time is None:
            return 0
        return int((time.time() - self.status_start_time) / 60)
    
    def get_history(self) -> list:
        return self._history_cache
    
    def get_formatted_history(self, limit: int = 5) -> list:
        formatted = []
        for record in self._history_cache[-limit:]:
            status = record['status']
            duration = record['duration']
            desc = f"{status} - {duration}分钟"
            formatted.append((status, duration, desc))
        return formatted
    
    def get_daily_summary(self, day: date = None):
        """获取统计摘要"""
        if day is None:
            day = date.today()
        
        try:
            data = StatsDAO.get_daily_summary(day)
            if data:
                return data
        except Exception as e:
            print(f"[HistoryManager] Summary Error: {e}")
        
        return {
            'total_focus_time': 0,
            'total_work_time': 0,
            'total_entertainment_time': 0,
            'pull_back_count': 0
        }

    # 兼容旧逻辑
    def get_reminder_interval(self, duration: int, threshold: int = 30) -> int:
        if duration < threshold: return 999999
        excess = duration - threshold
        if excess < 5: return 300
        elif excess < 15: return 180
        else: return 120
    
    def should_remind(self, threshold: int = 30) -> bool:
        if self.current_status != 'entertainment': return False
        return self.get_current_duration() >= threshold
