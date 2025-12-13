try:
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore

class ReminderOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        
        # 获取屏幕尺寸
        # 注意：PySide6 和 PyQt5 在获取屏幕方面略有不同，但 primaryScreen() 通常都可用
        app = QtWidgets.QApplication.instance()
        screen = app.primaryScreen()
        geometry = screen.availableGeometry()
        self.setGeometry(geometry)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        
        self.label = QtWidgets.QLabel("注意：检测到您长时间处于娱乐状态！")
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 48px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 180);
                padding: 40px;
                border-radius: 20px;
            }
        """)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        
        # 添加阴影效果
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QtGui.QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.label.setGraphicsEffect(shadow)
        
        layout.addWidget(self.label)
        
        # 点击任意位置关闭
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.hide()
        
    def show_message(self, message):
        self.label.setText(message)
        self.show()
        # 自动在几秒后隐藏（可选，这里设为5秒）
        QtCore.QTimer.singleShot(5000, self.hide)
