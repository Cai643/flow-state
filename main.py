import sys
import os
import time

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal

# 导入自定义组件
from ui.component.float_ball import SuspensionBall
from ui.interaction_logic.pop_up import CardPopup
from ui.component.reminder import ReminderOverlay
import ui.component.focus_card as cardgen

# 导入 AI 模块
from ai.tool.tool import InputMonitor, ScreenAnalyzer
from ai.model import API

class MonitorThread(QtCore.QThread):
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
            # 1. Capture Data
            frame = self.analyzer.capture_screen()
            analysis_stats = self.analyzer.analyze_frame(frame)
            content_type, change_val = self.analyzer.detect_content_type(frame, self.last_frame)
            self.last_frame = frame
            
            input_stats = self.monitor.get_and_reset_stats()

            # 2. Prepare Data for API
            monitor_data = {
                'key_presses': input_stats['key_presses'],
                'mouse_clicks': input_stats['mouse_clicks'],
                'screen_change_rate': change_val,
                'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
            }

            # 3. Call API
            if API:
                try:
                    result = API.get_analysis(monitor_data)
                    self.status_updated.emit(result)
                except Exception as e:
                    print(f"API Error: {e}")
            
            time.sleep(1) # Check every second

    def stop(self):
        self.running = False
        self.monitor.stop()
        self.wait()

def ensure_card_png(path):
    """
    确保 focus_card.png 存在，如果不存在则生成。
    注意：由于旧的生成代码已被移除，这里不再生成静态图片。
    如果需要显示卡片，应该直接使用 FocusStatusCard 组件。
    为了兼容性，我们可以创建一个空白或默认的图片，或者修改调用逻辑。
    """
    if not os.path.exists(path):
        # 创建一个简单的空白/占位图片，防止报错
        img = QtGui.QImage(300, 400, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(img)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 绘制简单的圆角矩形背景
        painter.setBrush(QtGui.QColor(40, 40, 40, 200))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(0, 0, 300, 400, 20, 20)
        
        # 绘制文字
        painter.setPen(QtGui.QColor(255, 255, 255))
        font = QtGui.QFont("Microsoft YaHei", 12)
        painter.setFont(font)
        painter.drawText(img.rect(), QtCore.Qt.AlignCenter, "Focus Card")
        
        painter.end()
        img.save(path)

def main():
    """
    主程序入口。
    """
    app = QtWidgets.QApplication(sys.argv)
    
    # 确保资源目录存在
    assets_dir = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    card_path = os.path.join(assets_dir, "focus_card.png")
    ensure_card_png(card_path)
    
    # 1. 创建并显示悬浮球
    ball = SuspensionBall()
    ball.show()
    
    # 2. 创建弹窗 (CardPopup 需要 ball_size 来计算布局，SuspensionBall 尺寸为 43+margin*2，但实际球体是 43)
    # pop_up.py 默认 ball_size=64，我们传入实际球体大小或 widget 大小？
    # pop_up.py 逻辑: bottom_h = max(ball_size, 64)
    # 传入 widget 的高度更合适，确保对齐
    popup = CardPopup(card_path, ball_size=ball.height())

    # 3. 创建提醒遮罩
    reminder = ReminderOverlay()

    # 4. 交互逻辑连接
    
    # 鼠标悬停悬浮球：自动显示弹窗
    def on_ball_hover():
        if not popup.isVisible():
            popup.showFromBall(ball)
            
    # 连接 entered 信号 (悬浮球类中已定义)
    ball.entered.connect(on_ball_hover)
    
    # 点击悬浮球：切换弹窗显示 (保留作为辅助)
    def on_ball_clicked():
        if popup.isVisible():
            popup.hideToBall(ball)
        else:
            popup.showFromBall(ball)
    ball.clicked.connect(on_ball_clicked)
    
    # 悬浮球移动：弹窗跟随
    ball.positionChanged.connect(lambda pos: popup.followBall(ball))
    
    # 5. 启动 AI 监控线程
    monitor_thread = MonitorThread()
    
    def on_status_update(result):
        # 结果格式: {'status': 'working', 'duration': 120, 'message': '...'}
        status = result.get('status', 'idle')
        duration = result.get('duration', 0)
        
        # 5.1 检查提醒 (娱乐状态持续20秒以上)
        if status == 'entertainment' and duration > 20:
            reminder.show_message("检测到您长时间处于娱乐状态，请注意休息！")
            
        # 5.2 更新悬浮球状态
        status_map = {
            'working': 'focus',
            'entertainment': 'distract_lite', # 默认轻度分心
            'idle': 'rest'
        }
        
        # 根据时长升级分心状态
        ball_state = status_map.get(status, 'focus')
        if status == 'entertainment' and duration > 60:
            ball_state = 'distract_heavy'
            
        ball.update_state(ball_state)
        
        # 5.3 更新悬浮球微信息 (显示时长)
        mins = int(duration / 60) # 分钟
        if mins > 0:
            ball.update_data(text=f"{mins}m")
        else:
            ball.update_data(text="")
            
    monitor_thread.status_updated.connect(on_status_update)
    monitor_thread.start()
    
    # 6. 生成日报 (可选，启动时检查)
    report_path = os.path.join(assets_dir, "daily_summary_report.png")
    if not os.path.exists(report_path):
        try:
            from ui.component.report import daily_sum
            # 这里假设有一个生成函数，如果没有，则跳过
            pass 
        except Exception:
            pass

    # 运行主循环
    # 设置 quitOnLastWindowClosed 为 False，确保日报关闭时主程序（悬浮球）不退出
    app.setQuitOnLastWindowClosed(False)
    exit_code = app.exec()
    
    # 退出清理
    monitor_thread.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
