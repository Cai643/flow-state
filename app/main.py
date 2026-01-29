import sys
import os
import time
import queue

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets

from app.ui.widgets.float_ball import SuspensionBall
from app.ui.views.popup_view import CardPopup
from app.ui.widgets.dialogs.fatigue import FatigueReminderDialog
from app.ui.widgets.dialogs.reminder import EntertainmentReminder
# 移除 MonitorThread，改用 Queue 接收数据
from app.data import init_db

# ensure_card_png 已移除，因为不再使用 assets 目录和图片资源

def main(msg_queue=None):
    try:
        if hasattr(QtCore.Qt, 'AA_ShareOpenGLContexts'):
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    except Exception:
        pass

    # 初始化数据库 (主进程也需要，因为可能有 UI 直接读取)
    init_db()

    app = QtWidgets.QApplication(sys.argv)
    
    ball = SuspensionBall()
    ball.show()
    
    # 移除 image_path 参数，CardPopup 现在自绘内容
    popup = CardPopup(target_margin=(5, 7), ball_size=ball.height())
    # 修正：初始化时使用 0，不要使用 3600 这种模拟数据
    popup.update_focus_status({"status": "working", "duration": 0, "message": "初始化..."})

    entertainment_reminder = EntertainmentReminder()
    
    def on_ball_hover():
        if not popup.isVisible():
            popup.showFromBall(ball)
            
    ball.entered.connect(on_ball_hover)
    
    def on_ball_clicked():
        if popup.isVisible():
            popup.hideToBall(ball)
        else:
            popup.showFromBall(ball)
    ball.clicked.connect(on_ball_clicked)
    
    ball.positionChanged.connect(lambda pos: popup.followBall(ball))
    
    def on_status_update(result):
        # Using static data for demo as requested previously
        # result = {"status": "working", "duration": 3600, "message": ""}
        # 注意：这里我们使用从队列接收到的真实数据
        status = result.get('status', 'focus')
        duration = result.get('duration', 0) # 这是连续专注时长 (Focus Duration)
        current_activity_duration = result.get('current_activity_duration', 0) # 这是当前状态持续时长 (用于娱乐提醒)
        
        # 将真实数据传递给悬浮窗组件
        popup.update_focus_status(result)
        
        current_time = time.time()
        
        # ----------------------------------------------------
        # Fatigue Reminder Logic (Based on continuous focus duration)
        # ----------------------------------------------------
        if not hasattr(on_status_update, 'last_fatigue_remind_time'):
            on_status_update.last_fatigue_remind_time = 0
            
        # 动态获取疲劳阈值 (默认为 2700秒 / 45分钟)
        current_fatigue_threshold = 2700
        if hasattr(popup, 'card') and hasattr(popup.card, 'fatigue_threshold'):
            current_fatigue_threshold = popup.card.fatigue_threshold
            
        # 调试输出
        # print(f"[DEBUG] Duration: {duration}, Threshold: {current_fatigue_threshold}")
        
        # 当连续专注时长 >= 用户设定阈值
        if duration >= current_fatigue_threshold:
             # 距离上次提醒至少间隔 5 分钟
             # 增加调试：如果是第一次，或者间隔足够
            should_remind = False
            if current_time - on_status_update.last_fatigue_remind_time > 300:
                should_remind = True
            
            # 如果是刚启动(last_time=0)且已经超时，也应该提醒
            if on_status_update.last_fatigue_remind_time == 0:
                 should_remind = True
                 
            if should_remind:
                print(f"[MAIN] Triggering Fatigue Reminder: Focus Duration {duration}s")
                
                # 计算显示的分钟数
                minutes = int(duration / 60)
                
                # 确保在主线程安全调用 UI
                # 这里的 on_status_update 本身就在主线程 (通过 QTimer)
                on_status_update.fatigue_dialog = FatigueReminderDialog(severity='medium', duration=minutes)
                
                # 关键：确保 dialog 没有被其他窗口遮挡
                on_status_update.fatigue_dialog.setWindowFlags(
                    on_status_update.fatigue_dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                )
                on_status_update.fatigue_dialog.show()
                on_status_update.fatigue_dialog.raise_()
                on_status_update.fatigue_dialog.activateWindow()
                
                on_status_update.last_fatigue_remind_time = current_time

        # ----------------------------------------------------
        # Real-time Entertainment Reminder Logic (Based on live data)
        # ----------------------------------------------------
        if not hasattr(on_status_update, 'last_entertainment_remind_time'):
            on_status_update.last_entertainment_remind_time = 0
            
        # 只有当状态为娱乐，且当前状态持续时间 >= 60秒
        # 使用 current_activity_duration 而不是 duration (因为 duration 在娱乐时被置0了)
        # 关键修改：检查当前模式是否为 "focus" (专注模式)
        from app.data.services.history_service import ActivityHistoryManager
        current_mode = ActivityHistoryManager.get_current_mode()
        
        # 只有在专注模式下，才启用娱乐提醒
        if current_mode == "focus":
            # 动态获取当前配置的阈值
            # 这里的 entertainment_reminder.dialog 其实是 ReminderOverlay，并没有存储 threshold
            # 但 FocusCard 存了。popup.card_widget 就是 FocusCard 实例
            
            # 注意：用户已将 UI 上的阈值控制改为“疲劳阈值”，所以娱乐阈值现在不再可配置，固定为 2分钟 (120s)
            current_threshold = 120 
            
            # 使用动态阈值替代硬编码的 60
            if status == 'entertainment' and current_activity_duration >= current_threshold:
                # 距离上次提醒至少间隔 5 分钟 (300秒)，避免频繁打扰
                if current_time - on_status_update.last_entertainment_remind_time > 300:
                    print(f"[MAIN] Triggering Entertainment Reminder: Duration {current_activity_duration}s (Threshold: {current_threshold}s)")
                    
                    # 计算严重程度
                    if current_activity_duration > 1800: severity = 'high'
                    elif current_activity_duration > 600: severity = 'medium'
                    else: severity = 'low'
                    
                    entertainment_reminder._handle_entertainment_warning(status, current_activity_duration, severity)
                    on_status_update.last_entertainment_remind_time = current_time

        # ----------------------------------------------------

        status_map = {
            'working': 'focus',
            'entertainment': 'distract_lite',
            'idle': 'rest',
            'focus': 'focus'
        }
        
        ball_state = status_map.get(status, 'focus')
        if status == 'entertainment' and current_activity_duration > 60:
            ball_state = 'distract_heavy'
            
        ball.update_state(ball_state)
        
        mins = int(duration / 60)
        if mins > 0:
            ball.update_data(text=f"{mins}m")
        else:
            ball.update_data(text="")
            
    # --- 替换原来的 QThread 逻辑，使用定时器轮询 Queue ---
    if msg_queue:
        # 创建一个 QTimer 来定期检查队列
        queue_timer = QtCore.QTimer()
        queue_timer.setInterval(100) # 每 100ms 检查一次
        
        def check_queue():
            try:
                # 尝试从队列中获取所有待处理的消息
                while not msg_queue.empty():
                    result = msg_queue.get_nowait()
                    on_status_update(result)
                    
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[Main] Queue Error: {e}")
        
        queue_timer.timeout.connect(check_queue)
        queue_timer.start()
        
        # 将 timer 引用保存在 app 上防止被回收
        app.queue_timer = queue_timer
    
    # 尝试预加载日报模块（如果可用）
    try:
        from app.ui.widgets.report import daily as daily_sum
        pass 
    except Exception:
        pass

    app.setQuitOnLastWindowClosed(False)
    exit_code = app.exec()
    
    # monitor_thread.stop() # 不再需要停止线程，由 run.py 管理进程生命周期
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
