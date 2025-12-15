from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6 import QtCore as QtCore  # type: ignore
    from PySide6 import QtGui as QtGui  # type: ignore
    from PySide6 import QtWidgets as QtWidgets  # type: ignore
else:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
        QT_LIB = "PySide6"
    except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
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


class ReminderOverlay(QtWidgets.QDialog):
    """简单娱乐提醒界面 - 仅显示消息和三个操作按钮"""
    
    work_clicked = QtCore.Signal()
    snooze_clicked = QtCore.Signal()
    disable_clicked = QtCore.Signal()
    
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
        wa_no_activate = qt_const("WA_ShowWithoutActivating")
        if wa_no_activate is not None:
            self.setAttribute(wa_no_activate)
        
        # 获取屏幕尺寸
        app = QtWidgets.QApplication.instance()
        screen: Optional[Any] = None
        if app is not None:
            primary = getattr(app, "primaryScreen", None)
            if callable(primary):
                screen = primary()
            else:
                pass
        if screen is None:
            desktop = getattr(QtWidgets.QApplication, "desktop", None)
            screen = desktop() if callable(desktop) else None
        
        # 获取有效屏幕几何尺寸
        if screen is not None:
            geometry = screen.availableGeometry()
        else:
            geometry = QtCore.QRect(0, 0, 800, 600)
        
        # 设置窗口尺寸（更大、更舒适的提醒窗口）
        window_width = 700
        window_height = 500
        center_x = geometry.left() + (geometry.width() - window_width) // 2
        center_y = geometry.top() + (geometry.height() - window_height) // 2
        self.setGeometry(center_x, center_y, window_width, window_height)
        
        # 主容器 - 淡蓝色渐变背景，高透明度
        self.container = QtWidgets.QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(200, 230, 255, 200), stop:1 rgba(150, 200, 255, 200));
                border: none;
                border-radius: 16px;
            }
        """)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setAlignment(qt_const("AlignCenter"))
        main_layout.addWidget(self.container)
        
        # 容器内布局 - 增加内边距和间距
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(32)
        
        # 主消息 - 更温和的语气
        self.main_message = QtWidgets.QLabel("该休息一下了")
        self.main_message.setStyleSheet("""
            QLabel {
                color: #5a67d8;
                font-size: 36px;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """)
        self.main_message.setAlignment(qt_const("AlignCenter"))
        self.main_message.setWordWrap(True)
        layout.addWidget(self.main_message)
        
        # 分割线
        separator = QtWidgets.QFrame()
        hline = getattr(QtWidgets.QFrame, "HLine", None)
        if hline is not None:
            separator.setFrameShape(hline)
        else:
            try:
                separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            except Exception:
                separator.setFrameShape(4)
        separator.setStyleSheet("background-color: rgba(200, 210, 240, 0.4);")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # 鼓励语句 - 更积极的心理暗示
        self.encouragement = QtWidgets.QLabel("💪 坚持就是胜利，休息是为了走得更远")
        self.encouragement.setStyleSheet("""
            QLabel {
                color: #48bb78;
                font-size: 15px;
                font-weight: bold;
                padding: 16px;
                background-color: rgba(72, 187, 120, 0.08);
                border-radius: 10px;
                border-left: 4px solid #48bb78;
            }
        """)
        self.encouragement.setAlignment(qt_const("AlignCenter"))
        self.encouragement.setWordWrap(True)
        layout.addWidget(self.encouragement)
        
        # 添加伸缩空间
        layout.addStretch()
        
        # 操作按钮栏 - 更柔和的按钮样式
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(16)
        button_layout.setAlignment(qt_const("AlignCenter"))
        
        # 按钮1：继续工作 - 温暖的黄色
        work_button = QtWidgets.QPushButton("继续工作 💪")
        work_button.setMinimumHeight(52)
        work_button.setMinimumWidth(150)
        work_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fbbf24, stop:1 #f59e0b);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fcd34d, stop:1 #fbbf24);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f59e0b, stop:1 #d97706);
            }
        """)
        work_button.clicked.connect(self.on_work_button)
        button_layout.addWidget(work_button)
        
        # 按钮2：再休息5分钟 - 柔和的蓝色
        snooze_button = QtWidgets.QPushButton("再休息5分钟 ☕")
        snooze_button.setMinimumHeight(52)
        snooze_button.setMinimumWidth(150)
        snooze_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #93c5fd, stop:1 #60a5fa);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
            }
        """)
        snooze_button.clicked.connect(self.on_snooze_button)
        button_layout.addWidget(snooze_button)
        
        # 按钮3：禁用提醒 - 柔和的灰色
        disable_button = QtWidgets.QPushButton("暂时禁用 ✕")
        disable_button.setMinimumHeight(52)
        disable_button.setMinimumWidth(150)
        disable_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d1d5db, stop:1 #9ca3af);
                color: #374151;
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e5e7eb, stop:1 #d1d5db);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9ca3af, stop:1 #6b7280);
            }
        """)
        disable_button.clicked.connect(self.on_disable_button)
        button_layout.addWidget(disable_button)
        
        layout.addLayout(button_layout)
        
        # 点击关闭
        self.setCursor(qt_const("PointingHandCursor"))
        
        # 动画效果
        self.fade_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)

    def mousePressEvent(self, event):
        """点击关闭"""
        self.close_reminder()
    
    def keyPressEvent(self, event):
        """Esc 键关闭"""
        if event.key() == QtCore.Qt.Key_Escape:
            self.close_reminder()
        else:
            super().keyPressEvent(event)
    
    def hideEvent(self, event):
        """隐藏事件处理"""
        if not self._is_closing:
            event.ignore()  # 保留窗口，但不强制显示
        else:
            super().hideEvent(event)
    
    def on_work_button(self):
        """用户点击'回去工作'按钮"""
        # 显示激励语
        self.main_message.setText("太棒了！🎯")
        self.encouragement.setText("你做的很对，专注才能成就梦想！\n加油，我看好你！💪")
        self.work_clicked.emit()
        # 延迟关闭，让用户看到激励语
        QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def on_snooze_button(self):
        """用户点击'再休息5分钟'按钮"""
        # 显示激励语
        self.main_message.setText("好的，休息一下～ ☕")
        self.encouragement.setText("放松心情，5分钟后我们继续加油！\n你的坚持会有回报的！✨")
        self.snooze_clicked.emit()
        # 延迟关闭，让用户看到激励语
        QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def on_disable_button(self):
        """用户点击'禁用提醒'按钮"""
        # 显示激励语
        self.main_message.setText("理解你～")
        self.encouragement.setText("希望你能自觉安排时间。\n记住，自律是通往成功的钥匙！🔑")
        self.disable_clicked.emit()
        # 延迟关闭，让用户看到激励语
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
    
    def show_reminder(self, data: dict):
        """显示智能提醒"""
        # 根据严重级别自定义消息
        severity = data.get('severity', 'low')
        duration = data.get('duration', 0)  # 持续时间（秒），需要转换为分钟
        minutes = int(duration / 60) if duration else 22
        
        # 温暖友好的提醒消息
        if severity == 'low':
            message = f"你已经看了 {minutes} 分钟视频啦～\n是不是被剧情吸引住了？没关系，\n要不要试试换件事做？✨"
            encouragement = "💪 休息一下，然后继续加油！"
        elif severity == 'medium':
            message = f"你已经追剧 {minutes} 分钟了呢～\n时间过得可真快！\n不过是时候回到工作上了吧？😊"
            encouragement = "🎯 坚持一下，好事儿在后头！"
        else:  # high
            message = f"哇，{minutes} 分钟了！\n你真的很投入呢～\n但现在真的该认真工作了哦！"
            encouragement = "✨ 冲冲冲，你可以的！"
        
        self.main_message.setText(message)
        self.encouragement.setText(encouragement)
        
        # 显示窗口
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()
