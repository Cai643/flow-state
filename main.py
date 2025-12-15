import sys
import os
import time

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPainter, QColor, QFont

# 导入自定义组件
from ui.component.float_ball import SuspensionBall
from ui.interaction_logic.pop_up import CardPopup
from ui.component.reminder_simple import ReminderOverlay
from ui.component.reminder_simple import ReminderOverlay as SimpleReminderOverlay
import ui.component.focus_card as cardgen
from ui.interaction_logic.reminder_logic import EntertainmentReminder

# 导入 AI 模块
from ai.tool.tool import InputMonitor, ScreenAnalyzer, get_active_window_title
from ai.model import API
# from ui.component.html_reminder_window import ReminderOverlayWebBased
from ui.component.fatigue_reminder_qt import FatigueReminderWindow
from fatigue_reminder_simple import FatigueReminderDialog


class MonitorThread(QThread):
    """
    后台监控线程：采集输入与屏幕数据，调用 API，并通过信号向主线程发送状态结果。
    """
    status_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.monitor = InputMonitor()
        self.analyzer = ScreenAnalyzer()
        self.last_frame = None

    def run(self):
        self.monitor.start()
        while self.running:
            try:
                # 1. 采集数据
                frame = self.analyzer.capture_screen()
                analysis_stats = self.analyzer.analyze_frame(frame)
                content_type, change_val = self.analyzer.detect_content_type(frame, self.last_frame)
                self.last_frame = frame

                input_stats = self.monitor.get_and_reset_stats()
                active_window = get_active_window_title()

                # 2. 组装数据
                monitor_data = {
                    'key_presses': input_stats.get('key_presses', 0),
                    'mouse_clicks': input_stats.get('mouse_clicks', 0),
                    'screen_change_rate': change_val,
                    'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False,
                    'content_type': content_type,
                    'active_window': active_window
                }

                # 3. 调用 API
                if API:
                    try:
                        result = API.get_analysis(monitor_data)
                        if isinstance(result, dict):
                            self.status_updated.emit(result)
                    except Exception as e:
                        print(f"[MonitorThread] API Error: {e}")

                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                print(f"[MonitorThread] Error in run loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

    def stop(self):
        self.running = False
        self.monitor.stop()
        self.wait()

def ensure_card_png(path):
    """
    确保 focus_card.png 存在，如果不存在则生成。
    """
    if not os.path.exists(path):
        try:
            # 创建一个简单的空白/占位图片，防止报错
            img = QImage(300, 400, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制简单的圆角矩形背景
            painter.setBrush(QColor(40, 40, 40, 200))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, 300, 400, 20, 20)
            
            # 绘制文字
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Microsoft YaHei", 12)
            painter.setFont(font)
            painter.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "Focus Card")
            
            painter.end()
            img.save(path)
            print(f"[ensure_card_png] PNG created at {path}")
        except Exception as e:
            print(f"[ensure_card_png] Error: {e}")


def main():
    """
    主程序入口。
    """
    print("[MAIN] ====== 程序启动 ======", flush=True)
    
    try:
        app = QtWidgets.QApplication(sys.argv)
        print("[MAIN] QApplication 创建完成", flush=True)
    except Exception as e:
        print(f"[MAIN] ERROR 创建 QApplication 失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 确保资源目录存在
    assets_dir = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    card_path = os.path.join(assets_dir, "focus_card.png")
    ensure_card_png(card_path)
    print("[MAIN] 资源目录和 PNG 初始化完成", flush=True)
    
    # 1. 创建并显示悬浮球
    ball = None
    try:
        print("[MAIN] 创建 SuspensionBall...", flush=True)
        ball = SuspensionBall()
        print(f"[MAIN] SuspensionBall 创建完成，大小: {ball.size()}", flush=True)
        ball.show()
        print(f"[MAIN] SuspensionBall 已显示，位置: {ball.pos()}", flush=True)
    except Exception as e:
        print(f"[MAIN] ERROR 创建悬浮球失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 2. 创建弹窗
    popup = None
    try:
        print("[MAIN] 创建 CardPopup...", flush=True)
        popup = CardPopup(card_path, ball_size=ball.height())
        # 确保弹窗有合理的最小尺寸，防止白屏
        popup.setMinimumSize(280, 200)
        print("[MAIN] CardPopup 创建完成", flush=True)
    except Exception as e:
        print(f"[MAIN] ERROR 创建 CardPopup 失败: {e}")
        import traceback
        traceback.print_exc()
        popup = None

    # 3. 创建提醒遮罩
    reminder = None
    fatigue_window = None
    try:
        print("[MAIN] 创建提醒遮罩...", flush=True)
        reminder = ReminderOverlay()
        simple_reminder = SimpleReminderOverlay()
        fatigue_window = FatigueReminderWindow()
        print("[MAIN] 提醒遮罩创建完成", flush=True)
    except Exception as e:
        print(f"[MAIN] ERROR 创建提醒遮罩失败: {e}")
        import traceback
        traceback.print_exc()
        reminder = None
        simple_reminder = None
        fatigueer = None
        html_reminder_window = None
    
    # 初始化娱乐提醒逻辑模块
    entertainment_logic = None
    try:
        if simple_reminder:
            entertainment_logic = EntertainmentReminder(overlay=simple_reminder)
            print("[MAIN] EntertainmentReminder 初始化完成")
    except Exception as e:
        print(f"[MAIN] ERROR 初始化 EntertainmentReminder 失败: {e}")

    # 追踪娱乐状态的开始时间
    entertainment_start_time = None
    entertainment_reminder_shown = False

    # 4. 交互逻辑连接
    
    # 鼠标悬停悬浮球：自动显示弹窗
    def on_ball_hover():
        if popup and not popup.isVisible():
            try:
                popup.showFromBall(ball)
            except Exception as e:
                print(f"[on_ball_hover] Error: {e}")
            
    # 连接 entered 信号
    ball.entered.connect(on_ball_hover)
    
    # 点击悬浮球：切换弹窗显示
    def on_ball_clicked():
        if popup:
            try:
                if popup.isVisible():
                    popup.hideToBall(ball)
                else:
                    popup.showFromBall(ball)
            except Exception as e:
                print(f"[on_ball_clicked] Error: {e}")
    ball.clicked.connect(on_ball_clicked)
    
    # 悬浮球移动：弹窗跟随
    if popup:
        ball.positionChanged.connect(lambda pos: popup.followBall(ball))
    
    # 5. 启动 AI 监控线程
    monitor_thread = None
    try:
        print("[MAIN] 创建 MonitorThread...", flush=True)
        monitor_thread = MonitorThread()
        print("[MAIN] MonitorThread 创建完成", flush=True)
    except Exception as e:
        print(f"[MAIN] ERROR 创建 MonitorThread 失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 定义状态更新回调
    def on_status_update(result):
        nonlocal entertainment_start_time, entertainment_reminder_shown
        
        try:
            status = result.get('status', 'idle')
            duration = result.get('duration', 0)
            
            # ========== 疲劳休息提醒逻辑 ==========
            # (已移除旧的错误实现，改用 main 函数中的 QTimer)
            
            # ========== 娱乐时间过长提醒逻辑 (使用 EntertainmentReminder) ==========
            if entertainment_logic:
                try:
                    entertainment_logic.on_status_update(result)
                except Exception as e:
                    print(f"[on_status_update] Error in entertainment_logic: {e}")
            
            # ========== 更新悬浮球状态 ==========
            status_map = {
                'working': 'focus',
                'entertainment': 'distract_lite',
                'idle': 'rest'
            }
            
            ball_state = status_map.get(status, 'focus')
            if status == 'entertainment' and duration > 60:
                ball_state = 'distract_heavy'
            
            try:
                ball.update_state(ball_state)
            except Exception as e:
                print(f"[on_status_update] Error updating ball state: {e}")
            
            # 更新悬浮球微信息 (显示时长)
            mins = int(duration / 60)
            try:
                if mins > 0:
                    ball.update_data(text=f"{mins}m")
                else:
                    ball.update_data(text="")
            except Exception as e:
                print(f"[on_status_update] Error updating ball data: {e}")
                
        except Exception as e:
            print(f"[MAIN] ERROR in on_status_update: {e}")
            import traceback
            traceback.print_exc()
    
    monitor_thread.status_updated.connect(on_status_update)
    print("[MAIN] 启动 MonitorThread...", flush=True)
    monitor_thread.start()
    print("[MAIN] MonitorThread 已启动", flush=True)
    
    # 6. 生成日报 (可选，启动时检查)
    report_path = os.path.join(assets_dir, "daily_summary_report.png")
    if not os.path.exists(report_path):
        try:
            from ui.component.report import daily_sum
        except Exception:
            pass

    # 30秒后显示疲劳提醒 (Added per user request)
    def show_fatigue_reminder_test():
        print("[MAIN] 30秒已到，显示疲劳提醒测试 (FatigueReminderWindow)")
        # 随机选择严重程度
        import random
        severity = random.choice(['low', 'medium', 'high'])
        durations = {'low': 30, 'medium': 120, 'high': 240}

        # 优先使用新版 Qt 提醒窗口
        if fatigue_window:
            try:
                fatigue_window.show_reminder(duration=durations[severity])
                return
            except Exception as e:
                print(f"[MAIN] ERROR 显示 FatigueReminderWindow 失败，回退到 Dialog: {e}")

        # 回退到旧的 Dialog 方案
        dialog = FatigueReminderDialog(severity=severity, duration=durations[severity])
        dialog.exec()

    QtCore.QTimer.singleShot(30000, show_fatigue_reminder_test)

    # 运行主循环
    print("[MAIN] 设置应用属性...", flush=True)
    app.setQuitOnLastWindowClosed(False)
    print("[MAIN] 进入事件循环...", flush=True)
    exit_code = app.exec()
    
    # 退出清理
    print("[MAIN] 清理资源...", flush=True)
    if monitor_thread:
        monitor_thread.stop()
    print("[MAIN] 程序退出", flush=True)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
