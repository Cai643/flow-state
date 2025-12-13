try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

class TimeAxisCard(QtWidgets.QWidget):
    """
    时光轴卡片：图标 + 标题 + 数据 (毛玻璃极夜风 - 方案A)
    尺寸：64x64px
    """
    clicked = Signal()

    def __init__(self, icon, title, data, tooltip, parent=None):
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        self.icon_text = icon
        self.title_text = title
        self.data_text = data
        self.setToolTip(tooltip)
        
        # 内部状态
        self._hover = False
        self._rotation = 0.0
        self._scale = 1.0
        self._opacity = 1.0
        
        # 动画对象
        self.hover_anim = None
        self.anim_group = None

    def enterEvent(self, event):
        self._hover = True
        self.start_hover_anim(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.start_hover_anim(False)
        super().leaveEvent(event)

    def start_hover_anim(self, entering):
        if self.hover_anim:
            self.hover_anim.stop()
        
        self.hover_anim = QtCore.QPropertyAnimation(self, b"scale_factor")
        self.hover_anim.setDuration(150)
        self.hover_anim.setEndValue(1.05 if entering else 1.0)
        self.hover_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        self.hover_anim.start()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

    # --- 属性定义 ---
    @Property(float)
    def scale_factor(self): return self._scale
    @scale_factor.setter
    def scale_factor(self, v):
        self._scale = v
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        
        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        
        # 坐标变换：中心缩放
        painter.translate(cx, cy)
        painter.scale(self._scale, self._scale)
        painter.translate(-cx, -cy)
        
        # 方案A 参数
        # 背景：rgba(168, 216, 234, 0.08) -> ~20
        # 边框：1px solid rgba(168, 216, 234, 0.25) -> ~64
        # 悬停边框：rgba(168, 216, 234, 0.5) -> ~128
        
        bg_alpha = 20
        border_alpha = 128 if self._hover else 64
        
        bg_color = QtGui.QColor(168, 216, 234, bg_alpha)
        border_color = QtGui.QColor(168, 216, 234, border_alpha)
        
        # 增加边距防止缩放截断 (64x64, scale 1.05 -> ~67.2)
        # 需要预留至少 2px 边距
        rect = QtCore.QRectF(3, 3, w-6, h-6)
        radius = 12
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, radius, radius)
        
        painter.setPen(QtGui.QPen(border_color, 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        
        # 1. 绘制图标 (Emoji 24px 居中)
        font_icon = QtGui.QFont("Segoe UI Emoji", 18) 
        if hasattr(font_icon, "setStyleHint"):
            font_icon.setStyleHint(QtGui.QFont.TypeWriter)
        painter.setFont(font_icon)
        painter.setPen(QtGui.QColor(255, 255, 255))
        
        # 图标位置：顶部偏下一点
        icon_rect = QtCore.QRectF(0, 8, w, 24)
        painter.drawText(icon_rect, QtCore.Qt.AlignCenter, self.icon_text)
        
        # 2. 绘制标题 (12px, 600, #a8d8ea)
        font_title = QtGui.QFont("Microsoft YaHei", 9) # 9pt approx 12px
        font_title.setWeight(QtGui.QFont.DemiBold) # 600
        painter.setFont(font_title)
        painter.setPen(QtGui.QColor("#a8d8ea"))
        
        title_rect = QtCore.QRectF(0, 32, w, 16)
        painter.drawText(title_rect, QtCore.Qt.AlignCenter, self.title_text)
        
        # 3. 绘制数据 (10px, 400, rgba(168,216,234,0.6))
        font_data = QtGui.QFont("Microsoft YaHei", 8) # 8pt approx 10-11px
        font_data.setWeight(QtGui.QFont.Normal)
        painter.setFont(font_data)
        painter.setPen(QtGui.QColor(168, 216, 234, 153)) # 0.6 * 255
        
        data_rect = QtCore.QRectF(0, 48, w, 14)
        painter.drawText(data_rect, QtCore.Qt.AlignCenter, self.data_text)


class TimeRetroBar(QtWidgets.QWidget):
    """
    时光回溯长条按钮
    样式：蓝色透明玻璃 (仿造 Scheme A 风格)
    """
    clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self.text = "是否时光回溯？"
        
        # 动画状态
        self._hover = False
        self._scale = 1.0
        self.anim = None
        
    def enterEvent(self, event):
        self._hover = True
        self.start_anim(True)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hover = False
        self.start_anim(False)
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
            
    def start_anim(self, hover):
        if self.anim:
            self.anim.stop()
        self.anim = QtCore.QPropertyAnimation(self, b"scale_val")
        self.anim.setDuration(200)
        self.anim.setEndValue(1.05 if hover else 1.0)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        self.anim.start()
        
    @Property(float)
    def scale_val(self): return self._scale
    @scale_val.setter
    def scale_val(self, v):
        self._scale = v
        self.update()
        
    def sizeHint(self):
        return QtCore.QSize(240, 50)
        
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        
        w = self.width()
        h = self.height()
        
        # 缩放中心
        cx, cy = w/2, h/2
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)
        
        # 蓝色透明玻璃风格 (参考 Scheme A 调色)
        # 稍微提高不透明度以保证文字可见性
        bg_color = QtGui.QColor(168, 216, 234, 40) # 0.15 * 255
        border_color = QtGui.QColor(168, 216, 234, 100) # 0.4 * 255
        
        # 增加边距以防止缩放时被截断
        # 宽度 200 * 1.05 ≈ 210，左右各需留出 5px 以上
        rect = QtCore.QRectF(6, 4, w-12, h-8)
        radius = rect.height() / 2 # 胶囊圆角
        
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg_color)
        p.drawRoundedRect(rect, radius, radius)
        
        p.setPen(QtGui.QPen(border_color, 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, radius, radius)
        
        # 绘制文字
        p.setPen(QtGui.QColor("#a8d8ea"))
        font = QtGui.QFont("Microsoft YaHei", 10)
        font.setBold(True)
        p.setFont(font)
        p.drawText(rect, QtCore.Qt.AlignCenter, self.text)


class HistoryEntryWidget(QtWidgets.QWidget):
    """
    历史记录入口组件
    状态1: 显示 '是否时光回溯？' 长条 (TimeRetroBar)
    状态2: 点击后显示三层时光轴 (TimeAxisCard x 3)
    """
    daily_clicked = Signal()
    weekly_clicked = Signal()
    monthly_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        
        # 布局
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # 状态1组件：长条按钮
        self.bar = TimeRetroBar(self)
        self.bar.clicked.connect(self.show_icons)
        self.layout.addWidget(self.bar)
        
        # 状态2组件容器：图标组 (初始隐藏)
        self.icons_container = QtWidgets.QWidget(self)
        self.icons_layout = QtWidgets.QHBoxLayout(self.icons_container)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(16) # 间距 16px (Scheme A)
        
        # 每日卡片
        self.card_daily = TimeAxisCard("📅", "日报", "7天", "昨日专注4.5h")
        self.card_daily.clicked.connect(self.daily_clicked.emit)
        self.icons_layout.addWidget(self.card_daily)
        
        # 每周卡片
        self.card_weekly = TimeAxisCard("📆", "周报", "4周", "本周29h")
        self.card_weekly.clicked.connect(self.weekly_clicked.emit)
        self.icons_layout.addWidget(self.card_weekly)
        
        # 每月卡片
        self.card_monthly = TimeAxisCard("🗓️", "月报", "1月", "本月98h")
        self.card_monthly.clicked.connect(self.monthly_clicked.emit)
        self.icons_layout.addWidget(self.card_monthly)
        
        self.layout.addWidget(self.icons_container)
        self.icons_container.hide()
        
        # 整体高度适应
        self.setFixedHeight(64) # 匹配卡片高度

    def show_icons(self):
        """切换到图标显示模式"""
        self.bar.hide()
        self.icons_container.show()
        
        # 触发动画：依次淡入/缩放
        self.animate_card(self.card_daily, 0)
        self.animate_card(self.card_weekly, 100)
        self.animate_card(self.card_monthly, 200)
        
    def animate_card(self, card, delay):
        anim = QtCore.QPropertyAnimation(card, b"scale_factor", self)
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QtCore.QEasingCurve.OutBack)
        QtCore.QTimer.singleShot(delay, anim.start)
        
        # 确保初始状态正确
        card._scale = 0.0
        
    def reset(self):
        """重置回长条状态 (可供外部调用)"""
        self.icons_container.hide()
        self.bar.show()
        
    def sizeHint(self):
        return QtCore.QSize(230, 50)

    def paintEvent(self, event):
        # 容器本身透明
        pass

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    # 测试窗口背景色为深色
    test_win = QtWidgets.QWidget()
    test_win.setStyleSheet("background-color: #0a0f1e;")
    test_win.resize(400, 200)
    
    layout = QtWidgets.QVBoxLayout(test_win)
    
    label = QtWidgets.QLabel("Scheme A Test")
    label.setStyleSheet("color: #a8d8ea;")
    layout.addWidget(label)
    
    entry = HistoryEntryWidget()
    layout.addWidget(entry)
    
    test_win.show()
    sys.exit(app.exec())
