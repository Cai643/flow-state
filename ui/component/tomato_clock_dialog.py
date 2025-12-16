"""
[正在使用]
番茄钟确认弹窗。
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

class TomatoClockDialog(QtWidgets.QDialog):
    """番茄钟开启确认弹窗"""
    
    if hasattr(QtCore, 'Signal'):
        Signal = QtCore.Signal
    else:
        Signal = QtCore.pyqtSignal
        
    start_tomato_clicked = Signal()
    cancel_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True) # 模态对话框
        self.setWindowFlags(
            qt_const("FramelessWindowHint")
            | qt_const("WindowStaysOnTopHint")
        )
        
        wa_translucent = qt_const("WA_TranslucentBackground")
        if wa_translucent is not None:
            self.setAttribute(wa_translucent)
            
        # 尺寸设置 (比提醒弹窗小一点)
        self.setFixedSize(500, 350)
        
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("TomatoDialog")
        try:
            from ui.component.report.report_theme import theme as MorandiTheme
        except ImportError:
            try:
                from .report.report_theme import theme as MorandiTheme
            except ImportError:
                from ui.component.report.report_theme import theme as MorandiTheme
        gradient_start = MorandiTheme.HEX_REMINDER_GRADIENT_START
        gradient_end = MorandiTheme.HEX_REMINDER_GRADIENT_END
        panel_fill = MorandiTheme.HEX_REMINDER_PANEL_FILL
        self.container.setStyleSheet(f"""
            QWidget#TomatoDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 {gradient_start},
                                            stop:1 {gradient_end});
                border-radius: 20px;
            }}
        """)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        # 容器内布局
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # 标题
        self.title_label = QtWidgets.QLabel("需要开番茄钟吗？")
        self.title_label.setAlignment(qt_const("AlignCenter"))
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: #5D4037;
                font-size: 26px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.title_label)
        
        # 说明文字
        self.desc_label = QtWidgets.QLabel("开启番茄钟，让我们专注25分钟，\n效率倍增！🍅")
        self.desc_label.setAlignment(qt_const("AlignCenter"))
        self.desc_label.setStyleSheet("""
            QLabel {
                color: #5D4037;
                font-size: 18px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.desc_label)
        
        # 按钮栏
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(30)
        button_layout.setAlignment(qt_const("AlignCenter"))
        
        # 按钮：是 (开启)
        yes_button = QtWidgets.QPushButton("是 (开启)")
        yes_button.setMinimumHeight(50)
        yes_button.setMinimumWidth(140)
        yes_button.setCursor(qt_const("PointingHandCursor"))
        yes_button.setStyleSheet(f"""
            QPushButton {{
                background: {panel_fill};
                color: #5D4037;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid #5D4037;
            }}
            QPushButton:hover {{
                background: #FFFFFF;
            }}
            QPushButton:pressed {{
                background: {panel_fill};
            }}
        """)
        yes_button.clicked.connect(self.on_yes)
        button_layout.addWidget(yes_button)
        
        # 按钮：否 (取消)
        no_button = QtWidgets.QPushButton("否 (不用了)")
        no_button.setMinimumHeight(50)
        no_button.setMinimumWidth(140)
        no_button.setCursor(qt_const("PointingHandCursor"))
        no_button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: #5D4037;
                border: 2px solid #5D4037;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {panel_fill};
            }}
            QPushButton:pressed {{
                background: #FFFFFF;
            }}
        """)
        no_button.clicked.connect(self.on_no)
        button_layout.addWidget(no_button)
        
        layout.addLayout(button_layout)
        
    def on_yes(self):
        self.start_tomato_clicked.emit()
        self.accept()
        
    def on_no(self):
        self.cancel_clicked.emit()
        self.reject()
