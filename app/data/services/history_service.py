# -*- coding: utf-8 -*-
"""
[正在使用]
活动历史管理器 (业务逻辑层)
负责管理活动状态的流转和记录。
通过 DAO 层与数据库交互。
"""

import time
from datetime import date
from app.data.dao.activity_dao import ActivityDAO, StatsDAO, WindowSessionDAO
import json

class ActivityHistoryManager:
    """活动历史管理器"""
    
    def __init__(self):
        self.current_status = None
        self.status_start_time = None
        self._last_summary = None
        self._last_raw_data = None
        
        # 记录当前连续专注时长 (秒)
        self._current_focus_streak_seconds = 0
        
        # 意志力胜利检测状态: 记录进入当前状态前，是否处于 Focus 状态
        self._last_status_was_focus = False
        
        # 新增：记录上一个窗口会话的信息，用于合并
        self._last_window_session = {
            'id': None,
            'title': None,
            'process': None
        }
        
        # 内存缓存，用于快速 UI 展示
        self._history_cache = [] 
    
    def update(self, status: str, summary: str = None, raw_data: str = None):
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
                # 检测意志力胜利 (从 Entertainment 切回 Focus)
                willpower_win_increment = 0
                if self.current_status == 'entertainment' and status in ['focus', 'work']:
                    if self._last_status_was_focus and 5 < duration_seconds < 300:
                        willpower_win_increment = 1
                
                self._save_record(self.current_status, duration_seconds, self._last_summary, self._last_raw_data, willpower_wins_increment=willpower_win_increment)
                self._update_cache(self.current_status, int(duration_seconds / 60), self.status_start_time)
            
            # 更新状态追踪 (为下一段做准备)
            if self.current_status in ['focus', 'work']:
                self._last_status_was_focus = True
            else:
                self._last_status_was_focus = False
                
            self.current_status = status
            self.status_start_time = current_time
            # 重置缓存的摘要
            self._last_summary = summary 
            self._last_raw_data = raw_data
            
            # 如果新状态直接带有详细信息（AI分析结果），立即保存一条快照，避免数据积压在内存
            if raw_data:
                 # 这里时长设为 0 或者当前已持续时间，视需求而定。
                 # 为了简单，我们让它作为一条"即时记录"被看到，但要注意不要和上面的 _save_record 重复统计时长
                 # 策略：更新 status_start_time，相当于开启了一段新记录
                 pass

        else:
            # 状态没变
            # 关键修改：如果收到了 raw_data (说明是 AI 分析结果)，强制保存当前这一段，并开启新的一段
            # 这样可以确保 AI 分析结果立即写入数据库，而不是等状态改变
            if raw_data:
                duration_seconds = int(current_time - self.status_start_time)
                # 即使时间很短，只要有 AI 分析结果，也值得保存
                if duration_seconds > 0:
                     self._save_record(self.current_status, duration_seconds, summary, raw_data)
                     self._update_cache(self.current_status, int(duration_seconds / 60), self.status_start_time)
                
                # 重置开始时间，相当于无缝开启下一段同状态的记录
                self.status_start_time = current_time
                self._last_summary = summary
                self._last_raw_data = raw_data
            
            else:
                # 只是普通的心跳更新，更新缓存即可
                if summary:
                    self._last_summary = summary
                if raw_data:
                    self._last_raw_data = raw_data
    
    def _save_record(self, status: str, duration: int, summary: str = None, raw_data: str = None, willpower_wins_increment: int = 0):
        """调用 DAO 保存数据"""
        try:
            # 1. 写入流水日志
            # 使用本地时间作为时间戳，解决时区问题
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ActivityDAO.insert_log(status, duration, timestamp=timestamp, summary=summary, raw_data=raw_data)
            
            # 2. 计算连续专注时长
            if status in ['focus', 'work']:
                self._current_focus_streak_seconds += duration
            else:
                # 状态中断，重置 (可以加一个宽容度逻辑，比如 <2分钟的娱乐不打断，但这里先严格处理)
                self._current_focus_streak_seconds = 0
            
            # 3. 更新每日统计 (传入当前连续时长)
            today = date.today()
            StatsDAO.update_daily_stats(today, status, duration, self._current_focus_streak_seconds, willpower_wins_increment)
            
            # 4. 更新或创建窗口会话聚合记录 (Window Sessions)
            if raw_data:
                try:
                    rd = json.loads(raw_data)
                    window_title = rd.get('window', '')
                    process_name = rd.get('process', '')
                    
                    # 检查是否是同一个窗口会话的延续
                    # 注意：这里我们简单比对窗口标题。如果需要更严谨，可以比对进程名。
                    # 还需要考虑 Session 的时间间隔，但这里 duration 已经是连续的片段。
                    
                    # 获取数据库中最后一条记录（用于恢复上下文，比如程序重启后）
                    # 优化：优先使用内存缓存，如果没有（首次运行），再查库
                    if self._last_window_session['id'] is None:
                        last_sess = WindowSessionDAO.get_last_session()
                        if last_sess:
                            self._last_window_session = {
                                'id': last_sess['id'],
                                'title': last_sess['window_title'],
                                'process': last_sess['process_name']
                            }
                    
                    is_same_session = (
                        self._last_window_session['id'] is not None and
                        window_title == self._last_window_session['title']
                        # process_name == self._last_window_session['process'] # 可选：严格匹配进程
                    )
                    
                    if is_same_session:
                        # 是同一个会话，更新时长
                        WindowSessionDAO.update_session_duration(self._last_window_session['id'], duration)
                        
                        # 关键新增：如果新的 summary 是有效的（不是窗口标题），且与旧的不同，则更新
                        # 判断是否为有效 AI 摘要：通常 summary 会包含"活动摘要"等字样，或者长度不同，
                        # 简单逻辑：只要 summary 不为空且不等于窗口标题，就认为是更有价值的信息
                        if summary and summary != window_title:
                            # 也可以加一个判断，避免被旧的覆盖？通常最新的总是更准
                            WindowSessionDAO.update_session_summary(self._last_window_session['id'], summary)
                    else:
                        # 是新会话，创建新记录
                        # start_time 应该是当前时间减去 duration (因为 duration 是刚刚过去的时间)
                        start_ts = time.time() - duration
                        
                        WindowSessionDAO.create_session(
                            window_title, process_name, start_ts, duration, status, summary
                        )
                        
                        # 更新缓存，指向新创建的 Session
                        # 注意：create_session 没有返回 ID，我们需要再次查询或者修改 DAO 返回 ID
                        # 这里简单处理：再查一次 ID (并发低时问题不大)
                        new_sess = WindowSessionDAO.get_last_session()
                        if new_sess:
                            self._last_window_session = {
                                'id': new_sess['id'],
                                'title': new_sess['window_title'],
                                'process': new_sess['process_name']
                            }
                            
                except Exception as e:
                    print(f"[HistoryManager] Session Merge Error: {e}")
                    
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
        pass
        # try:
        #     OcrDAO.insert_record(content, app_name, screenshot_path)
        # except Exception as e:
        #     print(f"[HistoryManager] OCR DB Error: {e}")

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
    
    def get_daily_logs(self, day: date = None):
        """获取某日的详细活动日志"""
        if day is None:
            day = date.today()
        try:
            return ActivityDAO.get_logs_by_date(day)
        except Exception as e:
            print(f"[HistoryManager] Logs Error: {e}")
            return []

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
