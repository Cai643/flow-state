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
from app.services.reminder.manager import EntertainmentReminder
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
    popup.update_focus_status({"status": "working", "duration": 3600, "message": ""})

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
        duration = result.get('duration', 0)
        popup.update_focus_status(result)
        
        # Fatigue reminder logic
        if not hasattr(on_status_update, 'app_start_time'):
            on_status_update.app_start_time = time.time()
        
        if not hasattr(on_status_update, 'fatigue_reminder_shown'):
            on_status_update.fatigue_reminder_shown = False
        
        if not on_status_update.fatigue_reminder_shown:
            elapsed_time = time.time() - on_status_update.app_start_time
            if elapsed_time >= 15:  
                on_status_update.fatigue_reminder_shown = True
                print("[MAIN] 程序运行 15 秒，弹出疲劳休息提醒")
                minutes = 60
                on_status_update.fatigue_dialog = FatigueReminderDialog(severity='medium', duration=minutes)
                on_status_update.fatigue_dialog.show()
        
        # Entertainment reminder logic
        if not hasattr(on_status_update, 'test_entertainment_shown'):
            on_status_update.test_entertainment_shown = False
            
        elapsed_time = time.time() - on_status_update.app_start_time

        if elapsed_time >= 60 and not on_status_update.test_entertainment_shown:
            on_status_update.test_entertainment_shown = True
            print("[MAIN] 程序运行已达60秒，触发一次预设娱乐提醒")
            entertainment_reminder._handle_entertainment_warning('entertainment', 60, 'medium')

        status_map = {
            'working': 'focus',
            'entertainment': 'distract_lite',
            'idle': 'rest',
            'focus': 'focus'
        }
        
        ball_state = status_map.get(status, 'focus')
        if status == 'entertainment' and duration > 60:
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
