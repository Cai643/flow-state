import sys
import time
import queue
try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtWidgets

from app.ui.widgets.float_ball import SuspensionBall
from app.ui.views.popup_view import CardPopup
from app.ui.widgets.dialogs.fatigue import FatigueReminderDialog
from app.ui.widgets.dialogs.reminder import EntertainmentReminder
from app.data import init_db
from app.data.services.history_service import ActivityHistoryManager

class FlowStateApp(QtCore.QObject):
    def __init__(self, msg_queue=None):
        super().__init__()
        self.msg_queue = msg_queue
        
        # 1. 初始化数据库
        init_db()
        
        # 2. 初始化 UI 组件
        self.ball = SuspensionBall()
        self.popup = CardPopup(target_margin=(5, 7), ball_size=self.ball.height())
        self.popup.update_focus_status({"status": "working", "duration": 0, "message": "初始化..."})
        
        self.entertainment_reminder = EntertainmentReminder()
        
        # 3. 绑定事件
        self._setup_connections()
        
        # 4. 显示悬浮球
        self.ball.show()
        
        # 5. 状态追踪变量
        self.last_fatigue_remind_time = 0
        self.last_entertainment_remind_time = 0
        self.fatigue_dialog = None
        
        # 6. 启动消息队列轮询
        if self.msg_queue:
            self.queue_timer = QtCore.QTimer()
            self.queue_timer.setInterval(100)
            self.queue_timer.timeout.connect(self._check_queue)
            self.queue_timer.start()

    def _setup_connections(self):
        # 悬浮球交互
        self.ball.entered.connect(self._on_ball_hover)
        self.ball.clicked.connect(self._on_ball_clicked)
        self.ball.positionChanged.connect(lambda pos: self.popup.followBall(self.ball))

    def _on_ball_hover(self):
        if not self.popup.isVisible():
            self.popup.showFromBall(self.ball)

    def _on_ball_clicked(self):
        if self.popup.isVisible():
            self.popup.hideToBall(self.ball)
        else:
            self.popup.showFromBall(self.ball)

    def _check_queue(self):
        try:
            while not self.msg_queue.empty():
                result = self.msg_queue.get_nowait()
                self._handle_status_update(result)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[AppManager] Queue Error: {e}")

    def _handle_status_update(self, result):
        # 1. 更新 UI 数据
        status = result.get('status', 'focus')
        duration = result.get('duration', 0)
        current_activity_duration = result.get('current_activity_duration', 0)
        
        self.popup.update_focus_status(result)
        
        current_time = time.time()
        
        # 2. 疲劳提醒逻辑
        self._check_fatigue(duration, current_time)
        
        # 3. 娱乐提醒逻辑
        self._check_entertainment(status, current_activity_duration, current_time)
        
        # 4. 更新悬浮球状态
        self._update_ball_state(status, current_activity_duration, duration)

    def _check_fatigue(self, duration, current_time):
        # 获取阈值
        current_fatigue_threshold = 2700
        if hasattr(self.popup, 'card') and hasattr(self.popup.card, 'fatigue_threshold'):
            current_fatigue_threshold = self.popup.card.fatigue_threshold
            
        # 阈值为 0 表示关闭
        if current_fatigue_threshold > 0 and duration >= current_fatigue_threshold:
            should_remind = False
            # 间隔 5 分钟
            if current_time - self.last_fatigue_remind_time > 300:
                should_remind = True
            # 首次触发
            if self.last_fatigue_remind_time == 0:
                should_remind = True
                
            if should_remind:
                print(f"[App] Triggering Fatigue Reminder: {duration}s")
                minutes = int(duration / 60)
                
                self.fatigue_dialog = FatigueReminderDialog(severity='medium', duration=minutes)
                self.fatigue_dialog.setWindowFlags(
                    self.fatigue_dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                )
                self.fatigue_dialog.show()
                self.fatigue_dialog.raise_()
                self.fatigue_dialog.activateWindow()
                
                self.last_fatigue_remind_time = current_time

    def _check_entertainment(self, status, duration, current_time):
        current_mode = ActivityHistoryManager.get_current_mode()
        
        if current_mode == "focus":
            current_threshold = 60
            if status == 'entertainment' and duration >= current_threshold:
                if current_time - self.last_entertainment_remind_time > 300:
                    print(f"[App] Triggering Entertainment Reminder: {duration}s")
                    
                    if duration > 1800: severity = 'high'
                    elif duration > 600: severity = 'medium'
                    else: severity = 'low'
                    
                    self.entertainment_reminder._handle_entertainment_warning(status, duration, severity)
                    self.last_entertainment_remind_time = current_time

    def _update_ball_state(self, status, current_activity_duration, duration):
        status_map = {
            'working': 'focus',
            'entertainment': 'distract_lite',
            'idle': 'rest',
            'focus': 'focus'
        }
        
        ball_state = status_map.get(status, 'focus')
        if status == 'entertainment' and current_activity_duration > 60:
            ball_state = 'distract_heavy'
            
        self.ball.update_state(ball_state)
        
        mins = int(duration / 60)
        if mins > 0:
            self.ball.update_data(text=f"{mins}m")
        else:
            self.ball.update_data(text="")
