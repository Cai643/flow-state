import os
import sys
import time

# 尝试导入 PySide6，如果不存在或加载失败则回退到 PyQt5
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    QT = "PySide6"
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    QT = "PyQt5"
    Signal = QtCore.pyqtSignal

# 导入自定义组件
from ui.component.float_ball import SuspensionBall
from ui.interaction_logic.pop_up import CardPopup, ImageOverlay
from ui.component.reminder import ReminderOverlay

# 导入 AI 模块
from ai.tool.tool import InputMonitor, ScreenAnalyzer
from ai.model import API

class MonitorThread(QtCore.QThread):
    status_updated = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def run(self):
        monitor = InputMonitor()
        monitor.start()
        analyzer_tool = ScreenAnalyzer()
        last_frame = None
        
        while self.running:
            try:
                # 1. 获取数据
                frame = analyzer_tool.capture_screen()
                content_type, change_val = analyzer_tool.detect_content_type(frame, last_frame)
                last_frame = frame
                
                analysis_stats = analyzer_tool.analyze_frame(frame)
                input_stats = monitor.get_and_reset_stats()
                
                # 2. 构造数据包
                monitor_data = {
                    'key_presses': input_stats['key_presses'],
                    'mouse_clicks': input_stats['mouse_clicks'],
                    'screen_change_rate': change_val,
                    'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
                }
                
                # 3. API 分析
                result = API.get_analysis(monitor_data)
                self.status_updated.emit(result)
                
                time.sleep(2)
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(2)
        
        monitor.stop()

    def stop(self):
        self.running = False
        self.wait()

def main():
    """
    主程序入口。
    """
    # 启用高 DPI 支持（让悬浮球在高清屏上更清晰）
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    
    # 确保资源目录存在（日报等图片输出会使用）
    assets_dir = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    # 创建并显示悬浮球
    ball = SuspensionBall()
    ball.show()
    
    # 创建弹窗：内置实时专注卡片
    # 悬浮球组件尺寸为 59x59 (43 + 8*2)
    popup = CardPopup(ball_size=59)

    # 创建提醒遮罩
    reminder = ReminderOverlay()

    # 启动监控线程
    monitor_thread = MonitorThread()
    
    def on_status_update(result):
        # 1. 检查提醒
        if result['status'] == 'entertainment' and result.get('duration', 0) > 20:
            reminder.show_message("检测到您长时间处于娱乐状态，请注意休息！")
            
        # 2. 更新悬浮球状态
        status_map = {
            'working': 'focus',
            'entertainment': 'distract_lite', # 默认轻度分心
            'idle': 'rest'
        }
        
        # 根据时长升级分心状态
        ball_state = status_map.get(result['status'], 'focus')
        if result['status'] == 'entertainment' and result.get('duration', 0) > 60:
            ball_state = 'distract_heavy'
            
        ball.update_state(ball_state)
        
        # 3. 更新悬浮球微信息 (显示时长)
        duration = int(result.get('duration', 0) / 60) # 分钟
        if duration > 0:
            ball.update_data(text=f"{duration}m")
        else:
            ball.update_data(text="")
            
    monitor_thread.status_updated.connect(on_status_update)
    monitor_thread.status_updated.connect(popup.update_focus_status)
    monitor_thread.start()
    
    # 退出时停止线程
    app.aboutToQuit.connect(monitor_thread.stop)

    # 交互逻辑
    def on_touch():
        popup.showFromBall(ball)

    def show_full_report():
        report_path = os.path.join(os.getcwd(), "assets", "daily_summary_report.png")
        if not os.path.exists(report_path):
            try:
                import assets.daily_summary_report as reportgen
                reportgen.create_daily_summary()
            except Exception:
                pass
        if os.path.exists(report_path):
            overlay = ImageOverlay(report_path)
            overlay.show()
            setattr(popup, "_overlay", overlay)
            overlay.closed.connect(lambda: setattr(popup, "_overlay", None))

    # 连接信号
    ball.entered.connect(on_touch)
    ball.positionChanged.connect(lambda *_: popup.followBall(ball))
    ball.left.connect(lambda *_: popup.hideToBall(ball))
    popup.request_full_report.connect(show_full_report)
    
    # 启动事件循环
    if QT == "PyQt5":
        sys.exit(app.exec_())
    else:
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
