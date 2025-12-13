import sys
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    QT = "PySide6"
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    QT = "PyQt5"

class TaijiBall(QtWidgets.QWidget):
    touched = Signal()
    entered = Signal()
    positionChanged = Signal(QtCore.QPoint)
    left = Signal()
    def __init__(self, size=64, color_a=QtGui.QColor(0, 255, 0), color_b=QtGui.QColor(0, 200, 0)):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(size, size)
        self.color_a = color_a  # 渐变结束色（外圈）
        self.color_b = color_b  # 渐变起始色（中心）
        self.border_width = 2
        self.border_alpha = 180
        self.border_color = QtGui.QColor(0, 0, 0, self.border_alpha)
        self.drag_offset = None
        self.updateMask()
        self.moveToBottomRight()

        # 呼吸灯相关属性
        self.breath_value = 0.0  # 呼吸动画当前值 (0.0 - 1.0)
        self.breath_direction = 1  # 呼吸方向：1为增强，-1为减弱
        
        # 创建定时器驱动呼吸动画
        self.breath_timer = QtCore.QTimer(self)
        self.breath_timer.timeout.connect(self.updateBreath)
        self.breath_timer.start(50)  # 每50ms更新一次

    def updateBreath(self):
        """
        更新呼吸灯状态。
        """
        step = 0.05
        self.breath_value += step * self.breath_direction
        
        # 边界检查与反转方向
        if self.breath_value >= 1.0:
            self.breath_value = 1.0
            self.breath_direction = -1
        elif self.breath_value <= 0.0:
            self.breath_value = 0.0
            self.breath_direction = 1
            
        self.update()  # 触发重绘

    def updateMask(self):
        r = QtCore.QRect(0, 0, self.width(), self.height())
        self.setMask(QtGui.QRegion(r, QtGui.QRegion.Ellipse))

    def moveToBottomRight(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        m = 20
        x = geo.right() - self.width() - m
        y = geo.bottom() - self.height() - m
        self.move(x, y)

    def enterEvent(self, event):
        self.border_alpha = 0
        self.border_color.setAlpha(self.border_alpha)
        self.update()
        self.entered.emit()

    def leaveEvent(self, event):
        self.border_alpha = 180
        self.border_color.setAlpha(self.border_alpha)
        self.update()
        self.left.emit()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            self.touched.emit()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and self.drag_offset is not None:
            self.move(event.globalPos() - self.drag_offset)
            self.positionChanged.emit(self.pos())
            event.accept()

    def moveEvent(self, event):
        try:
            self.positionChanged.emit(self.pos())
        finally:
            super().moveEvent(event)

    def resizeEvent(self, event):
        self.updateMask()
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = QtCore.QRectF(0, 0, self.width(), self.height())
        r = min(self.width(), self.height()) / 2.0
        cx = rect.center().x()
        cy = rect.center().y()
        p.setPen(QtCore.Qt.NoPen)
        
        # 绘制主体的渐变背景
        # 使用线性渐变，从上(0,0)到下(0, height)
        grad = QtGui.QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, self.color_b)  # 顶部颜色
        grad.setColorAt(1.0, self.color_a)  # 底部颜色
        p.setBrush(QtGui.QBrush(grad))
        p.drawEllipse(rect)
        
        # 绘制呼吸灯光晕效果（确保在最上层绘制）
        # 计算光晕颜色：使用白色，根据 breath_value 调整透明度
        glow_color = QtGui.QColor(255, 255, 255)  # 纯白色光晕
        min_alpha = 30   # 最小透明度
        max_alpha = 180  # 最大透明度
        current_alpha = int(min_alpha + (max_alpha - min_alpha) * self.breath_value)
        glow_color.setAlpha(current_alpha)
        
        # 光晕渐变：外圈亮，向内透明
        glow_grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), r)
        glow_grad.setColorAt(0.85, QtGui.QColor(255, 255, 255, 0))  # 内部完全透明
        glow_grad.setColorAt(0.95, glow_color)                      # 边缘发光
        glow_grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))   # 最外层渐隐
        
        p.setBrush(QtGui.QBrush(glow_grad))
        p.drawEllipse(rect)

