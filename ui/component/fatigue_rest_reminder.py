from typing import Any, Optional, TYPE_CHECKING
import os
import json

if TYPE_CHECKING:
    from PySide6 import QtCore as QtCore  # type: ignore
    from PySide6 import QtGui as QtGui  # type: ignore
    from PySide6 import QtWidgets as QtWidgets  # type: ignore
    from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
else:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
        from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
        QT_LIB = "PySide6"
    except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
        from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
        QT_LIB = "PyQt5"

def qt_const(name: str) -> Any:
    qt = getattr(QtCore, "Qt", None)
    if qt is None:
        return None
    val = getattr(qt, name, None)
    if val is not None:
        return val
    for enum_name in ("WindowType", "WidgetAttribute", "CursorShape", "AlignmentFlag"):
        enum = getattr(qt, enum_name, None)
        if enum is not None:
            sub = getattr(enum, name, None)
            if sub is not None:
                return sub
    return None


class FatigueRestReminder(QtWidgets.QDialog):
    """疲劳休息提醒窗口 - 使用 HTML 美观界面"""
    
    rest_selected = QtCore.Signal(str)  # 传递选中的休息方式
    closed = QtCore.Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(
            qt_const("FramelessWindowHint")
            | qt_const("WindowStaysOnTopHint")
        )
        
        self._is_closing = False
        
        wa_translucent = qt_const("WA_TranslucentBackground")
        if wa_translucent is not None:
            self.setAttribute(wa_translucent)
        
        # 获取屏幕尺寸
        app = QtWidgets.QApplication.instance()
        screen: Optional[Any] = None
        if app is not None:
            primary = getattr(app, "primaryScreen", None)
            if callable(primary):
                screen = primary()
        if screen is None:
            desktop = getattr(QtWidgets.QApplication, "desktop", None)
            screen = desktop() if callable(desktop) else None
        
        if screen is not None:
            geometry = screen.availableGeometry()
        else:
            geometry = QtCore.QRect(0, 0, 1000, 700)
        
        # 设置窗口尺寸
        window_width = 900
        window_height = 650
        center_x = geometry.left() + (geometry.width() - window_width) // 2
        center_y = geometry.top() + (geometry.height() - window_height) // 2
        self.setGeometry(center_x, center_y, window_width, window_height)
        
        # 创建 WebEngineView
        self.web_view = QWebEngineView(self)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.web_view)
        
        # 获取 HTML 文件路径
        import pathlib
        # 获取项目根目录
        project_root = pathlib.Path(__file__).parent.parent.parent
        html_path = str(project_root / 'fatigue_reminder_demo.html')
        
        # 加载 HTML 文件
        if os.path.exists(html_path):
            print(f"[INFO] 加载 HTML 文件: {html_path}")
            self.web_view.load(QtCore.QUrl.fromLocalFile(html_path))
        else:
            # 显示空白页面，包含错误提示
            error_html = f"<html><body><h1>Error: HTML file not found</h1><p>{html_path}</p></body></html>"
            self.web_view.setHtml(error_html)
            print(f"[ERROR] HTML 文件不存在: {html_path}")
        
        # JavaScript 桥接
        try:
            self.web_view.page().javaScriptConsoleMessage.connect(self._on_js_message)
        except AttributeError:
            # 某些版本兼容性问题
            print("[WARNING] JavaScript 控制台消息信号不可用")
        
        # 注册 JavaScript 函数
        self._setup_js_bridge()
        
        # 动画效果
        self.fade_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)
        
        # 设置窗口不透明度
        self.setWindowOpacity(1.0)
    
    def _setup_js_bridge(self):
        """设置 JavaScript 到 Python 的桥接"""
        # 在页面加载完成后，注入 JavaScript 函数
        def inject_bridge():
            js_code = """
            window.pyBridge = {
                selectSuggestion: function(title) {
                    console.log('SELECT_SUGGESTION:' + title);
                },
                handleContinue: function() {
                    console.log('CONTINUE_WORK');
                },
                handleSnooze: function(minutes) {
                    console.log('SNOOZE:' + minutes);
                }
            };
            """
            self.web_view.page().runJavaScript(js_code)
        
        self.web_view.loadFinished.connect(inject_bridge)
    
    def _on_js_message(self, level, message, line_number, source_id):
        """处理 JavaScript 控制台消息"""
        print(f"[JS] {message}")
        
        if message.startswith('SELECT_SUGGESTION:'):
            suggestion = message.replace('SELECT_SUGGESTION:', '')
            print(f"[INFO] 用户选择了休息方式: {suggestion}")
            self.rest_selected.emit(suggestion)
            QtCore.QTimer.singleShot(1500, self.close_reminder)
        
        elif message == 'CONTINUE_WORK':
            print("[INFO] 用户选择继续工作")
            self.rest_selected.emit('continue')
            QtCore.QTimer.singleShot(1500, self.close_reminder)
        
        elif message.startswith('SNOOZE:'):
            minutes = message.replace('SNOOZE:', '')
            print(f"[INFO] 用户选择延后 {minutes} 分钟")
            self.rest_selected.emit(f'snooze_{minutes}')
            QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def close_reminder(self):
        """关闭提醒"""
        self._is_closing = True
        self.fade_out_and_close()
    
    def fade_out_and_close(self):
        """淡出动画"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(lambda: self.hide())
        self.fade_animation.start()
    
    def show_reminder(self, duration: int = 0):
        """显示休息提醒
        
        Args:
            duration: 工作时长（秒）
        """
        # 更新 HTML 中的工作时长显示
        if duration > 0:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            duration_text = f"工作时长: {hours}小时{minutes}分钟"
            
            js_code = f"""
            document.querySelector('.duration').textContent = '{duration_text}';
            """
            self.web_view.page().runJavaScript(js_code)
        
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()
    
    def keyPressEvent(self, event):
        """Esc 键关闭"""
        if event.key() == QtCore.Qt.Key_Escape:
            self.close_reminder()
        else:
            super().keyPressEvent(event)
