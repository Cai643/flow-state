"""
[正在使用]
用于显示"娱乐时间过长"的简单提醒弹窗。
被 ui.interaction_logic.reminder_logic.EntertainmentReminder 调用。
包含 ReminderOverlay 类。
"""
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
    
    if hasattr(QtCore, 'Signal'):
        Signal = QtCore.Signal
    else:
        Signal = QtCore.pyqtSignal
        
    work_clicked = Signal()
    snooze_clicked = Signal()
    disable_clicked = Signal()
    
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
        
        # 主容器 - 学生版护眼绿主题
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("VideoReminderDialog")  # 为了匹配 QSS
        self.container.setStyleSheet("""
            QWidget#VideoReminderDialog {
                background-color: #E8F5E9;  /* 淡绿背景，护眼 */
                border: 2px solid #A5D6A7;  /* 柔和边框 */
                border-radius: 20px;
            }
        """)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setAlignment(qt_const("AlignCenter"))
        main_layout.addWidget(self.container)
        
        # 容器内布局
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(25)
        
        # 1. 历史回顾区域 (新增)
        history_frame = QtWidgets.QFrame()
        history_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(66, 165, 245, 0.1);
                border-radius: 15px;
                border: 1px solid rgba(66, 165, 245, 0.2);
            }
        """)
        history_layout = QtWidgets.QVBoxLayout(history_frame)
        history_layout.setContentsMargins(25, 20, 25, 20)
        history_layout.setSpacing(8)
        
        # 上次专注时长
        self.focus_summary_label = QtWidgets.QLabel("📚 刚才你专注了32分钟")
        self.focus_summary_label.setObjectName("focus_summary")
        self.focus_summary_label.setAlignment(qt_const("AlignLeft"))
        self.focus_summary_label.setStyleSheet("""
            QLabel#focus_summary { 
                color: #1565C0;      /* 深蓝色 */ 
                font-size: 18px; 
                font-weight: bold; 
                background: transparent;
                border: none;
            } 
        """)
        history_layout.addWidget(self.focus_summary_label)
        
        # 专注内容
        self.focus_task_label = QtWidgets.QLabel("   在做：论文写作")
        self.focus_task_label.setObjectName("focus_task")
        self.focus_task_label.setAlignment(qt_const("AlignLeft"))
        self.focus_task_label.setStyleSheet("""
            QLabel#focus_task { 
                color: #546E7A;      /* 蓝灰色 */ 
                font-size: 16px; 
                background: transparent;
                border: none;
            } 
        """)
        history_layout.addWidget(self.focus_task_label)
        
        layout.addWidget(history_frame)

        # 2. 消息内容区域 (Frame包裹)
        msg_frame = QtWidgets.QFrame()
        msg_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.4);
                border-radius: 15px;
                border: 1px solid rgba(255, 213, 79, 0.3);
            }
        """)
        msg_layout = QtWidgets.QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(30, 25, 30, 25)
        msg_layout.setSpacing(12)
        
        # 主消息
        self.main_message = QtWidgets.QLabel("🌿 电量充得差不多啦！")
        self.main_message.setObjectName("message")
        self.main_message.setAlignment(qt_const("AlignLeft")) # 改为左对齐
        self.main_message.setWordWrap(True)
        self.main_message.setStyleSheet("""
            QLabel#message { 
                color: #2E7D32;      /* 深绿色 */ 
                font-size: 22px; 
                font-weight: bold;
                background: transparent;
                border: none;
            } 
        """)
        msg_layout.addWidget(self.main_message)
        
        # 建议详情
        self.suggestion_detail = QtWidgets.QLabel("   休息8分钟后，现在回去效率最高！")
        self.suggestion_detail.setAlignment(qt_const("AlignLeft"))
        self.suggestion_detail.setWordWrap(True)
        self.suggestion_detail.setStyleSheet("""
            QLabel { 
                color: #4E342E;      /* 深棕色 */ 
                font-size: 16px; 
                background: transparent;
                border: none;
                margin-top: 5px;
            } 
        """)
        msg_layout.addWidget(self.suggestion_detail)
        
        # 鼓励语 (原 encouragement)
        self.encouragement = QtWidgets.QLabel("   论文思路还在热乎中，现在回去刚刚好！")
        self.encouragement.setAlignment(qt_const("AlignLeft"))
        self.encouragement.setWordWrap(True)
        self.encouragement.setStyleSheet("""
            QLabel { 
                color: #5D4037;      /* 棕色 */ 
                font-size: 16px; 
                background: transparent;
                border: none;
            } 
        """)
        msg_layout.addWidget(self.encouragement)
        
        layout.addWidget(msg_frame)
        
        # 添加伸缩空间
        layout.addStretch()
        
        # 3. 操作按钮栏
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(qt_const("AlignCenter"))
        
        # 按钮1：继续努力 (Primary)
        work_button = QtWidgets.QPushButton("继续努力 💪")
        work_button.setObjectName("primary")
        work_button.setMinimumHeight(55)
        work_button.setMinimumWidth(180)
        work_button.setCursor(qt_const("PointingHandCursor"))
        work_button.setStyleSheet("""
            QPushButton#primary { 
                background: #66BB6A; /* 自然绿按钮 */ 
                color: white; 
                border-radius: 15px; 
                font-size: 16px;
                font-weight: bold;
                border: none;
            } 
            QPushButton#primary:hover {
                background: #4CAF50;
            }
            QPushButton#primary:pressed {
                background: #388E3C;
            }
        """)
        work_button.clicked.connect(self.on_work_button)
        button_layout.addWidget(work_button)
        
        # 按钮2：再充5分钟 (Secondary)
        snooze_button = QtWidgets.QPushButton("再充5分钟电 🔋")
        snooze_button.setObjectName("secondary")
        snooze_button.setMinimumHeight(55)
        snooze_button.setMinimumWidth(180)
        snooze_button.setCursor(qt_const("PointingHandCursor"))
        snooze_button.setStyleSheet("""
            QPushButton#secondary { 
                background: transparent; 
                color: #66BB6A; 
                border: 2px solid #66BB6A; /* 加粗一点边框 */
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            } 
            QPushButton#secondary:hover {
                background: rgba(102, 187, 106, 0.1);
            }
            QPushButton#secondary:pressed {
                background: rgba(102, 187, 106, 0.2);
            }
        """)
        snooze_button.clicked.connect(self.on_snooze_button)
        button_layout.addWidget(snooze_button)
        
        layout.addLayout(button_layout)
        
        # 底部：暂时禁用 (更隐蔽的设计)
        disable_button = QtWidgets.QPushButton("今天不再提醒")
        disable_button.setCursor(qt_const("PointingHandCursor"))
        disable_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #A1887F;
                border: none;
                font-size: 13px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #8D6E63;
            }
        """)
        disable_button.clicked.connect(self.on_disable_button)
        layout.addWidget(disable_button, 0, qt_const("AlignCenter"))
        
        # 点击关闭
        # self.setCursor(qt_const("PointingHandCursor")) # 移除全局手型，避免干扰
        
        # 动画效果
        self.fade_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)

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
        # 确保至少显示 1 分钟，避免出现 "0 分钟"
        minutes = max(1, int(duration / 60)) if duration else 22
        
        # 优先使用传入的消息
        custom_message = data.get('message')
        custom_encouragement = data.get('encouragement')
        
        if custom_message:
            message = custom_message
        else:
            # 温暖友好的提醒消息
            if severity == 'low':
                message = f"你已经看了 {minutes} 分钟视频啦～\n是不是被剧情吸引住了？没关系，\n要不要试试换件事做？✨"
            elif severity == 'medium':
                message = f"你已经追剧 {minutes} 分钟了呢～\n时间过得可真快！\n不过是时候回到工作上了吧？😊"
            else:  # high
                message = f"哇，{minutes} 分钟了！\n你真的很投入呢～\n但现在真的该认真工作了哦！"
        
        if custom_encouragement:
            encouragement = custom_encouragement
        else:
            if severity == 'low':
                encouragement = "💪 休息一下，然后继续加油！"
            elif severity == 'medium':
                encouragement = "🎯 坚持一下，好事儿在后头！"
            else:
                encouragement = "✨ 冲冲冲，你可以的！"
        
        self.main_message.setText(message)
        self.encouragement.setText(encouragement)
        
        # 显示窗口
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()
