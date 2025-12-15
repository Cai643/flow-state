try:
    from PySide6 import QtCore  # type: ignore
except ImportError:
    from PyQt5 import QtCore  # type: ignore

import time
from typing import Optional

from ui.component.reminder_simple import ReminderOverlay
from ui.component.smart_reminder_generator import SmartReminderGenerator
from ui.component.activity_history_manager import ActivityHistoryManager
# from ui.component.fatigue_detector import FatigueDetector
# from ui.component.fatigue_reminder import FatigueReminder
# from ui.component.fatigue_reminder_dialog import FatigueReminderDialog


class EntertainmentReminder(QtCore.QObject):
    """智能娱乐提醒系统
    
    特性：
    - 渐进式提醒（温和 -> 关切 -> 紧急）
    - 个性化消息生成
    - 活动历史追踪
    - 可选语音提醒
    """
    
    def __init__(self, parent=None, threshold_duration=0.5, overlay=None):
        super().__init__(parent)
        self.threshold_duration = threshold_duration
        
        # UI组件
        if overlay:
            self.overlay = overlay
        else:
            self.overlay = ReminderOverlay(parent)
        
        # 智能组件
        self.message_generator = SmartReminderGenerator()
        self.history_manager = ActivityHistoryManager()
        
        # 提醒控制
        self.last_reminder_time = 0
        self.reminder_count = 0  # 连续提醒次数
        self.reminder_disabled = False  # 临时禁用提醒的标志
        self.snooze_until_time = 0  # 延后提醒的截止时间
        
        # 三阶段提醒标志
        self._reminded_at_22min = False
        self._reminded_at_35min = False
        self._reminded_at_50min = False
        
        # 用户选择记录（用于正强化）
        self.last_entertainment_duration = 0  # 上次娱乐持续时长
        self.show_work_encouragement = False  # 是否需要在下次专注时显示鼓励
        
        # 连接按钮信号
        self.overlay.work_clicked.connect(self.on_work_button)
        self.overlay.snooze_clicked.connect(self.on_snooze_button)
        self.overlay.disable_clicked.connect(self.on_disable_button)
        
        # 疲劳检测器
        # self.fatigue_detector = FatigueDetector()
        self.work_session_start = None  # 当前工作会话开始时间
        self.last_fatigue_check = 0  # 设为0，只有在真正工作时才开始检查
        self.fatigue_check_interval = 300  # 每5分钟检查一次
        
        # 疲惫提醒系统（连续工作超过5小时）
        # self.fatigue_reminder = FatigueReminder(parent)
        # self.fatigue_reminder.fatigue_reminder_triggered.connect(self._on_fatigue_reminder_triggered)
        self.current_fatigue_reminder_dialog = None
        
        # 语音支持（可选）
        self.voice_enabled = False
        self._init_voice_support()
    
    def _init_voice_support(self):
        """初始化语音支持（可选）"""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            
            # 配置语音参数
            self.tts_engine.setProperty('rate', 150)  # 语速
            self.tts_engine.setProperty('volume', 0.8)  # 音量
            
            # 尝试设置中文语音
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'mandarin' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            self.voice_enabled = True
            print("[OK] 语音提醒已启用")
        except Exception as e:
            print(f"[INFO] 语音提醒不可用: {e}")
            self.voice_enabled = False
            self.tts_engine = None
    
    def enable_voice(self, enabled: bool = True):
        """启用/禁用语音提醒"""
        if self.tts_engine:
            self.voice_enabled = enabled
    
    def on_status_update(self, result: dict):
        """状态更新回调
        
        Args:
            result: {'status': str, 'duration': int, 'message': str}
        """
        status = result.get("status")
        duration = result.get("duration", 0)
        
        # 更新活动历史
        self.history_manager.update(status)
        
        # ========== 疲惫提醒系统 ==========
        # 追踪工作活动以检测连续工作超过5小时
        # if status in ['focus', 'work']:
        #     self.fatigue_reminder.mark_activity()
        
        # 定期检查是否需要显示疲惫提醒
        # self.fatigue_reminder.check_idle_and_update()
        # fatigue_reminder_data = self.fatigue_reminder.check_fatigue_reminder()
        
        # ========== 原有提醒逻辑 ==========
        # 如果从娱乐切换到专注/工作，记录娱乐持续时长并显示鼓励
        if status in ['focus', 'work'] and self.show_work_encouragement:
            self._show_focus_encouragement()
            self.show_work_encouragement = False
        
        # 如果从其他状态回到娱乐，重新启用提醒
        if status in ["entertainment", "reading"]:  # 把reading也作为娱乐
            self.reminder_disabled = False
        else:
            # 从娱乐状态切换走时，记录持续时长，重置提醒标志
            prev_status = self.history_manager.current_status
            if prev_status in ["entertainment", "reading"]:
                self.last_entertainment_duration = self.history_manager.get_current_duration()
            # 重置三阶段提醒标志
            self._reminded_at_22min = False
            self._reminded_at_35min = False
            self._reminded_at_50min = False
            self.reminder_count = 0
        
        # 检查三个提醒时间点：10秒、20秒、30秒
        if status in ["entertainment", "reading"] and not self.reminder_disabled:
            current_time = time.time()
            if current_time >= self.snooze_until_time:
                # 10秒提醒
                if 10 <= duration < 20 and not self._reminded_at_22min:
                    self._reminded_at_22min = True
                    self._handle_entertainment_warning(status, duration, 'low')
                # 20秒提醒
                elif 20 <= duration < 30 and not self._reminded_at_35min:
                    self._reminded_at_35min = True
                    self._handle_entertainment_warning(status, duration, 'medium')
                # 30秒提醒
                elif duration >= 30 and not self._reminded_at_50min:
                    self._reminded_at_50min = True
                    self._handle_entertainment_warning(status, duration, 'high')
    
    def _handle_entertainment_warning(self, status: str, duration: int, severity: str = 'low'):
        """处理娱乐状态警告
        
        Args:
            status: 当前状态
            duration: 持续时间（分钟）
            severity: 严重级别 ('low', 'medium', 'high')
        """
        # 显示提醒
        self._show_smart_reminder(status, duration, severity)
    
    def _show_smart_reminder(self, status: str, duration: int, severity: str):
        """显示智能提醒
        
        Args:
            status: 当前状态
            duration: 持续时间（秒）
            severity: 严重级别
        """
        # 准备UI数据
        display_data = {
            'message': '娱乐时间太长，该回去工作了！',
            'icon': '📚',
            'history': [],
            'duration': duration,
            'threshold': int(self.threshold_duration * 60),
            'encouragement': '坚持工作，你可以的！',
            'severity': severity
        }
        
        # 显示UI
        self.overlay.show_reminder(display_data)
    
    def _speak_reminder(self, message: str, severity: str):
        """语音播报提醒
        
        Args:
            message: 提醒消息
            severity: 严重级别
        """
        if not self.tts_engine:
            return
        
        try:
            # 清理消息中的emoji和特殊符号
            clean_message = self._clean_message_for_speech(message)
            
            # 根据严重级别添加前缀
            if severity == 'high':
                speech = f"温馨提醒。{clean_message}"
            elif severity == 'medium':
                speech = f"温馨提醒。{clean_message}"
            else:
                speech = clean_message
            
            # 异步播报（不阻塞主线程）
            self.tts_engine.say(speech)
            self.tts_engine.runAndWait()
            
        except Exception as e:
            print(f"[ERROR] 语音播报失败: {e}")
    
    def on_work_button(self):
        """用户点击'回去工作'按钮"""
        print("[INFO] 用户选择回去工作")
        self.reminder_count = 0
        self.show_work_encouragement = True
    
    def on_snooze_button(self):
        """用户点击'再休息5分钟'按钮"""
        self.snooze_until_time = time.time() + 5 * 60  # 5分钟后
        print(f"[INFO] 用户选择再休息5分钟，延后提醒至 {self.snooze_until_time}")
    
    def on_disable_button(self):
        """用户点击'不需要提醒'按钮"""
        self.reminder_disabled = True
        print("[INFO] 用户临时禁用提醒，直到切换状态为止")
    
    def _show_focus_encouragement(self):
        """在用户切换到专注时显示鼓励"""
        if self.last_entertainment_duration > 0:
            print(f"[INFO] 用户从娱乐切换到专注，上次持续时长: {self.last_entertainment_duration} 分钟")
    
    def _clean_message_for_speech(self, message: str) -> str:
        """清理消息用于语音播报
        
        移除emoji和不适合语音的符号
        """
        import re
        
        # 移除emoji
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # 表情符号
            u"\U0001F300-\U0001F5FF"  # 符号和图标
            u"\U0001F680-\U0001F6FF"  # 交通和地图
            u"\U0001F1E0-\U0001F1FF"  # 旗帜
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        
        clean = emoji_pattern.sub('', message)
        
        # 移除特殊符号
        clean = clean.replace('⚠️', '').replace('🚨', '').replace('💥', '')
        clean = clean.replace('⏰', '').replace('🔔', '')
        
        return clean.strip()
    
    def get_statistics(self) -> dict:
        """获取统计数据"""
        return self.history_manager.get_summary()
    
    def reset_daily_stats(self):
        """重置每日统计"""
        self.history_manager._reset_daily_stats()
        self.reminder_count = 0
    
    def check_fatigue_level(self, key_presses: int = 0, mouse_clicks: int = 0, 
                           idle_time: int = 0) -> Optional[dict]:
        """定期检查疲劳水平（每5分钟调用一次）
        
        Args:
            key_presses: 最近时间内的键盘输入次数
            mouse_clicks: 最近时间内的鼠标点击次数
            idle_time: 空闲时间（秒）
            
        Returns:
            疲劳检测结果或None
        """
        # 只在用户处于工作/专注状态时检查疲劳
        if not self.work_session_start:
            return None
        
        current_time = time.time()
        consecutive_work_mins = (current_time - self.work_session_start) / 60
        
        # 只有工作超过30分钟才开始进行疲劳检测
        if consecutive_work_mins < 30:
            return None
        
        # 检查是否应该执行检查
        if current_time - self.last_fatigue_check < self.fatigue_check_interval:
            return None
        
        self.last_fatigue_check = current_time
        
        # 调用疲劳检测器
        # fatigue_level = self.fatigue_detector.calculate_fatigue_level(
        #     consecutive_work_mins,
        #     key_presses / max(1, 300),  # 归一化为每秒输入频率
        #     0  # 暂时不分析输入模式变化
        # )
        
        # result = {
        #     'fatigue_level': fatigue_level,
        #     'work_duration_mins': consecutive_work_mins,
        #     'input_frequency': key_presses / max(1, 300)
        # }
        
        # 如果检测到疲劳，显示提醒
        # if fatigue_level in ['fatigued', 'exhausted']:
        #     self._show_fatigue_reminder(result, fatigue_level)
        #     return result
        
        return None
    
    def _show_fatigue_reminder(self, metrics: dict, fatigue_level: str):
        """显示疲劳提醒 - 当前已禁用，只打印日志
        
        Args:
            metrics: 包含工作时长、输入频率等的指标字典
            fatigue_level: 'fatigued' 或 'exhausted'
        """
        work_duration = metrics.get('work_duration_mins', 0)
        
        # 只打印日志，不显示窗口
        if fatigue_level == 'exhausted':
            print(f"[FATIGUE] 严重疲劳检测：已连续工作 {int(work_duration)} 分钟")
        else:
            print(f"[FATIGUE] 轻度疲劳检测：已连续工作 {int(work_duration)} 分钟")
    
    def _on_fatigue_reminder_triggered(self, reminder_data: dict):
        """处理疲惫提醒信号
        
        Args:
            reminder_data: 包含工作时长和建议的提醒数据
        """
        # 创建并显示疲惫提醒对话框
        # dialog = FatigueReminderDialog(reminder_data)
        # self.current_fatigue_reminder_dialog = dialog
        
        # 连接信号
        # dialog.continue_working.connect(self._on_fatigue_continue_working)
        # dialog.snooze_clicked.connect(self._on_fatigue_snooze)
        # dialog.rest_selected.connect(self._on_rest_suggestion_selected)
        
        # 显示对话框
        # dialog.show()
        
        print(f"[FATIGUE_REMINDER] 显示疲惫提醒: {reminder_data.get('duration_formatted')}")
    
    def _on_fatigue_continue_working(self):
        """用户选择继续工作"""
        print("[FATIGUE_REMINDER] 用户选择继续工作")
        # 可以在这里添加鼓励或其他反馈
    
    def _on_fatigue_snooze(self, minutes: int):
        """用户选择延后提醒"""
        # self.fatigue_reminder.snooze_reminder(minutes)
        print(f"[FATIGUE_REMINDER] 用户选择延后 {minutes} 分钟提醒")
    
    def _on_rest_suggestion_selected(self, suggestion_title: str):
        """用户选择了一个休息建议"""
        print(f"[FATIGUE_REMINDER] 用户选择了休息方式: {suggestion_title}")
        # 可以在这里记录用户的休息选择
        # 或者显示该休息方式的更详细说明
    
    def track_focus_session(self, status: str):
        """追踪专注会话
        
        Args:
            status: 当前活动状态
        """
        if status in ['focus', 'work']:
            if not self.work_session_start:
                self.work_session_start = time.time()
        else:
            # 如果切换到其他状态，重置会话
            if self.work_session_start:
                session_duration = (time.time() - self.work_session_start) / 60
                print(f"[INFO] 工作会话结束，持续时长: {session_duration:.1f} 分钟")
            self.work_session_start = None



