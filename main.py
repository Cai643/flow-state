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
from ui.component.reminder_simple import ReminderOverlay
from ui.component.reminder_simple import ReminderOverlay as SimpleReminderOverlay
from ui.component.fatigue_reminder import FatigueReminderDialog
import ui.component.focus_card as cardgen
from ui.interaction_logic.reminder_logic import EntertainmentReminder

# 导入 AI 模块
from ai.tool.tool import CameraAnalyzer
from ai.model import API

class MonitorThread(QtCore.QThread):
    status_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.analyzer = CameraAnalyzer()
        self.last_frame = None

    def run(self):
        if not self.analyzer.start():
            print("[MonitorThread] Failed to start camera. Exiting thread.")
            return

        while self.running:
            # 1. Capture Data
            frame = self.analyzer.capture_frame()
            analysis_stats = self.analyzer.analyze_frame(frame)
            content_type, change_val = self.analyzer.detect_content_type(frame, self.last_frame)
            self.last_frame = frame
            
            # 2. Prepare Data for API
            monitor_data = {
                'key_presses': 0, # Camera only mode, no input monitoring
                'mouse_clicks': 0,
                'screen_change_rate': change_val, # Now represents camera movement/change
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
        self.analyzer.stop()
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
    # 尝试解决 WebEngineView 报错 (保留，以防万一未来用到)
    try:
        if hasattr(QtCore.Qt, 'AA_ShareOpenGLContexts'):
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    except Exception:
        pass

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
    # pop_up.py 逻辑: bottom_h = max(ball_size, 64)
    # 传入 widget 的高度更合适，确保对齐
    popup = CardPopup(card_path, ball_size=ball.height())

    # 3. 创建提醒遮罩
    # reminder = ReminderOverlay() # 移交给 EntertainmentReminder 管理
    # simple_reminder = SimpleReminderOverlay() # 移交给 EntertainmentReminder 管理
    
    # 初始化娱乐提醒逻辑模块
    entertainment_reminder = EntertainmentReminder()
    
    # 创建疲劳休息提醒 (已改为动态创建)
    
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
        
        # ========== 疲劳休息提醒逻辑 ==========
        # 初始化：程序启动时设置开始时间
        if not hasattr(on_status_update, 'app_start_time'):
            on_status_update.app_start_time = time.time()
        
        # 程序运行 15 秒后弹出疲劳提醒（仅显示一次）
        if not hasattr(on_status_update, 'fatigue_reminder_shown'):
            on_status_update.fatigue_reminder_shown = False
        
        if not on_status_update.fatigue_reminder_shown:
            elapsed_time = time.time() - on_status_update.app_start_time
            # 改为3分钟触发 (3 * 60 = 180秒)
            if elapsed_time >= 180:  
                on_status_update.fatigue_reminder_shown = True
                print("[MAIN] 程序运行 3 分钟，弹出疲劳休息提醒")
                
                # 使用新的原生弹窗，强制显示为 60 分钟
                minutes = 60
                
                # 保存引用防止被回收
                on_status_update.fatigue_dialog = FatigueReminderDialog(severity='medium', duration=minutes)
                on_status_update.fatigue_dialog.show()
        
        # [新增] 强制测试：程序运行5秒后弹出娱乐提醒
        if not hasattr(on_status_update, 'test_entertainment_shown'):
            on_status_update.test_entertainment_shown = False
            
        elapsed_time = time.time() - on_status_update.app_start_time
        
        if elapsed_time >= 5 and not on_status_update.test_entertainment_shown:
            on_status_update.test_entertainment_shown = True
            print("[MAIN] 程序运行已达5秒，强制触发娱乐提醒（测试）")
            # 模拟触发：状态=entertainment, 持续=10秒, 程度=low
            entertainment_reminder._handle_entertainment_warning('entertainment', 10, 'low')

        # ========== 娱乐时间过长提醒逻辑 ==========
        # 使用 EntertainmentReminder 模块处理
        entertainment_reminder.on_status_update(result)
        
        # ========== 更新悬浮球状态 ==========
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
