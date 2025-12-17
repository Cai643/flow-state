try:
    from PySide6 import QtCore, QtGui  # type: ignore
except ImportError:
    from PyQt5 import QtCore, QtGui  # type: ignore

import time
from typing import Optional

from ui.component.reminder_simple import ReminderOverlay
from ui.component.tomato_clock_dialog import TomatoClockDialog
from ui.component.smart_reminder_generator import SmartReminderGenerator
from data.activity_history_manager import ActivityHistoryManager
from ui.component.focus_card import TimerDialog


class EntertainmentReminder(QtCore.QObject):
    """智能娱乐提醒系统
    
    特性：
    - 渐进式提醒（温和 -> 关切 -> 紧急）
    - 个性化消息生成
    - 活动历史追踪
    - 可选语音提醒
    """
    
    def __init__(self, parent=None, threshold_duration=0.5):
        super().__init__(parent)
        self.threshold_duration = threshold_duration
        
        # UI组件
        self.overlay = ReminderOverlay(parent)
        self.tomato_dialog = None  # 延迟创建
        self.tomato_timer_dialog: Optional[TimerDialog] = None
        
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
        self.tomato_remaining_seconds = 0
        self.tomato_timer = QtCore.QTimer(self)
        self.tomato_timer.setInterval(1000)
        self.tomato_timer.timeout.connect(self._update_tomato_timer)
        
        # 连接按钮信号
        self.overlay.work_clicked.connect(self.on_work_button)
        self.overlay.snooze_clicked.connect(self.on_snooze_button)
        self.overlay.disable_clicked.connect(self.on_disable_button)
        
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
        
        # 检查三个提醒时间点：3秒、10秒、20秒
        if status in ["entertainment", "reading"] and not self.reminder_disabled:
            current_time = time.time()
            if current_time >= self.snooze_until_time:
                # 3秒提醒 (原10秒逻辑前移)
                if 3 <= duration < 10 and not self._reminded_at_22min:
                    self._reminded_at_22min = True
                    self._handle_entertainment_warning(status, duration, 'low')
                # 10秒提醒 (原20秒逻辑前移)
                elif 10 <= duration < 20 and not self._reminded_at_35min:
                    self._reminded_at_35min = True
                    self._handle_entertainment_warning(status, duration, 'medium')
                # 20秒提醒 (原30秒逻辑前移)
                elif duration >= 20 and not self._reminded_at_50min:
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
            duration: 持续时间（分钟）
            severity: 严重级别
        """
        # 1. 使用 SmartReminderGenerator 生成个性化文案
        # 注意：SmartReminderGenerator.generate_reminder 只需要 severity
        reminder_content = self.message_generator.generate_reminder(severity)
        
        # 2. 准备UI数据
        display_data = {
            'message': reminder_content.get('message', '该休息了'),
            'icon': reminder_content.get('icon', '📚'),
            'history': [],
            'duration': int(duration * 60),
            'threshold': int(self.threshold_duration * 60),
            'encouragement': reminder_content.get('encouragement', '坚持就是胜利'),
            'severity': severity
        }
        
        # 3. 显示UI (调用 ui.component.reminder_simple.ReminderOverlay)
        self.overlay.show_reminder(display_data)
        
        # 4. 触发语音提醒 (如果启用)
        if self.voice_enabled:
            self._speak_reminder(display_data['message'], severity)
    
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
        """用户点击'继续努力'按钮"""
        print("[INFO] 用户选择继续努力，弹出番茄钟确认")
        
        # 1. 关闭原来的提醒弹窗
        self.overlay.close_reminder()
        
        # 2. 弹出番茄钟确认弹窗
        if self.tomato_dialog is None:
            self.tomato_dialog = TomatoClockDialog(self.overlay.parent())
            self.tomato_dialog.start_tomato_clicked.connect(self._start_tomato_clock)
            self.tomato_dialog.cancel_clicked.connect(self._cancel_tomato)
        
        self.tomato_dialog.show()
        
    def _start_tomato_clock(self):
        """用户确认开启番茄钟"""
        print("[INFO] 用户确认开启番茄钟")
        self.reminder_count = 0
        self.show_work_encouragement = True

        if self.tomato_timer.isActive():
            self.tomato_timer.stop()

        if self.tomato_timer_dialog:
            try:
                self.tomato_timer_dialog.close()
            except Exception:
                pass
            self.tomato_timer_dialog = None

        duration_minutes = 25
        total_seconds = duration_minutes * 60

        try:
            self.tomato_timer_dialog = TimerDialog(self.overlay.parent())
            goal_text = f"番茄钟专注 {duration_minutes} 分钟"
            self.tomato_timer_dialog.end_session_requested.connect(self._cancel_tomato_clock)
            self.tomato_timer_dialog.start_session(goal_text, total_seconds)

            screen = None
            anchor_widget = None

            if self.tomato_dialog is not None and self.tomato_dialog.isVisible():
                anchor_widget = self.tomato_dialog
            elif self.overlay is not None and self.overlay.isVisible():
                anchor_widget = self.overlay

            if anchor_widget is not None:
                try:
                    geo = anchor_widget.frameGeometry()
                except Exception:
                    geo = anchor_widget.geometry()

                center = geo.center()
                if hasattr(QtGui.QGuiApplication, "screenAt"):
                    screen = QtGui.QGuiApplication.screenAt(center)

            if screen is None and hasattr(QtGui.QGuiApplication, "primaryScreen"):
                screen = QtGui.QGuiApplication.primaryScreen()

            if screen is not None:
                available = screen.availableGeometry()
                dialog_size = self.tomato_timer_dialog.size()
                if dialog_size.width() <= 0 or dialog_size.height() <= 0:
                    dialog_size = self.tomato_timer_dialog.sizeHint()
                x = available.right() - dialog_size.width() - 20
                y = available.bottom() - dialog_size.height() - 40
                min_x = available.left()
                max_x = available.right() - dialog_size.width()
                min_y = available.top()
                max_y = available.bottom() - dialog_size.height()
                if max_x < min_x:
                    max_x = min_x
                if max_y < min_y:
                    max_y = min_y
                x = max(min_x, min(x, max_x))
                y = max(min_y, min(y, max_y))
                self.tomato_timer_dialog.move(int(x), int(y))

            self.tomato_timer_dialog.show()
            try:
                self.tomato_timer_dialog.raise_()
                self.tomato_timer_dialog.activateWindow()
            except Exception:
                pass
        except Exception as e:
            print(f"[WARN] 无法创建番茄钟计时弹窗: {e}")
            self.tomato_timer_dialog = None

        self.tomato_remaining_seconds = total_seconds
        if self.tomato_remaining_seconds > 0:
            self.tomato_timer.start()

    def _update_tomato_timer(self):
        if self.tomato_remaining_seconds <= 0:
            self.tomato_timer.stop()
            return

        self.tomato_remaining_seconds -= 1

        if self.tomato_timer_dialog:
            try:
                self.tomato_timer_dialog.update_display(self.tomato_remaining_seconds)
            except Exception as e:
                print(f"[WARN] 更新番茄钟计时显示失败: {e}")

        if self.tomato_remaining_seconds <= 0:
            self.tomato_timer.stop()
        
    def _cancel_tomato(self):
        """用户取消开启番茄钟"""
        print("[INFO] 用户取消开启番茄钟，但仍视为回归工作")
        self.reminder_count = 0
        self.show_work_encouragement = True

    def _cancel_tomato_clock(self):
        if self.tomato_timer.isActive():
            self.tomato_timer.stop()
        self.tomato_remaining_seconds = 0
    
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
        # 注意：ActivityHistoryManager 可能没有 get_summary 方法，这里先注释掉或移除，避免报错
        # return self.history_manager.get_summary()
        return {}
