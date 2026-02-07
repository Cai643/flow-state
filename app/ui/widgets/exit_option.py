try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

class ExitOptionWidget(QtWidgets.QWidget):
    """
    退出程序选项框
    样式：仿造 TimeRetroBar，但尺寸较小
    行为：点击退出程序，点击外部消失
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 Popup 属性来实现点击外部自动关闭
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | 
            QtCore.Qt.Popup | 
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.text = "退出程序"
        self._hover = False
        
        # 尺寸设定：比今日回溯条(240x50)稍小
        self.setFixedSize(140, 40)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 兼容处理: PySide6 使用 position(), PyQt5 使用 pos()
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()
                
            # 只有当点击位置在控件内部时才退出
            if self.rect().contains(pos):
                QtCore.QCoreApplication.quit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        
        # 绘制背景
        # 配色参考 TimeRetroBar: #FEFAE0 (bg), #96C24B (border)
        
        bg_color = QtGui.QColor("#FEFAE0")
        border_color = QtGui.QColor("#96C24B")
        if self._hover:
            border_color = border_color.darker(110)
            
        # 留出一点边距给边框
        rect = QtCore.QRectF(2, 2, self.width()-4, self.height()-4)
        radius = rect.height() / 2
        
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg_color)
        p.drawRoundedRect(rect, radius, radius)
        
        p.setPen(QtGui.QPen(border_color, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, radius, radius)
        
        # 绘制文字
        p.setPen(QtGui.QColor("#5D4037"))
        font = QtGui.QFont("Microsoft YaHei", 10) 
        font.setBold(True)
        p.setFont(font)
        p.drawText(rect, QtCore.Qt.AlignCenter, self.text)
