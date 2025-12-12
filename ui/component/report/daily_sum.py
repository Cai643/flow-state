import sys
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

# --- 辅助类：带动画的数值 ---
class AnimatedValue(QtCore.QObject):
    valueChanged = Signal(float)
    
    def __init__(self, start_val=0.0):
        super().__init__()
        self._value = start_val
        self._anim = QtCore.QPropertyAnimation(self, b"value")
        
    @Property(float)
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self._value = v
        self.valueChanged.emit(v)
        
    def animate_to(self, end_val, duration=500, delay=0, easing=QtCore.QEasingCurve.OutQuad):
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(end_val)
        self._anim.setEasingCurve(easing)
        if delay > 0:
            QtCore.QTimer.singleShot(delay, self._anim.start)
        else:
            self._anim.start()

# --- 卡片组件 ---
class Card1_Focus(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        
        self.progress_val = AnimatedValue(0.0)
        self.progress_val.valueChanged.connect(self.update)
        
        # 启动动画
        # +30分钟: 延迟400ms
        self.slide_anim_val = AnimatedValue(0.0) # 0 to 1
        self.slide_anim_val.valueChanged.connect(self.update)
        self.slide_anim_val.animate_to(1.0, 200, 400)
        
        # 进度条: 延迟500ms
        self.progress_val.animate_to(0.5625, 600, 500) # 56.25%

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect()
        
        # 标题
        p.setPen(QtGui.QColor("#7f8c8d"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "🎯 今日专注时长")
        
        # 主数字
        p.setPen(QtGui.QColor("#3498db"))
        font_main = QtGui.QFont("Noto Sans SC", 24, QtGui.QFont.Bold)
        p.setFont(font_main)
        p.drawText(20, 60, "4.5小时")
        
        # 滑入的 "+30分钟"
        slide_progress = self.slide_anim_val.value
        if slide_progress > 0:
            p.setOpacity(slide_progress)
            x_offset = (1.0 - slide_progress) * 20
            p.setPen(QtGui.QColor("#e74c3c")) # 红色表示变化？原设计无指定颜色，假设强调色
            # 原设计: 纯色#3498db，无渐变
            p.setPen(QtGui.QColor("#3498db"))
            font_sub = QtGui.QFont("Noto Sans SC", 10)
            p.setFont(font_sub)
            p.drawText(int(140 + x_offset), 55, "↑ 比昨天 +30分钟")
            p.setOpacity(1.0)
            
        # 进度条背景
        bar_rect = QtCore.QRectF(20, 80, rect.width() - 40, 6)
        p.setBrush(QtGui.QColor("#ecf0f1"))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(bar_rect, 3, 3)
        
        # 进度条前景
        prog = self.progress_val.value
        if prog > 0:
            fill_width = bar_rect.width() * prog
            fill_rect = QtCore.QRectF(20, 80, fill_width, 6)
            p.setBrush(QtGui.QColor("#3498db"))
            p.drawRoundedRect(fill_rect, 3, 3)

class Card2_Distract(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 标题
        p.setPen(QtGui.QColor("#7f8c8d"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "🔔 今日分心次数")
        
        # 主数字
        p.setPen(QtGui.QColor("#2c3e50"))
        font_main = QtGui.QFont("Noto Sans SC", 16, QtGui.QFont.Bold)
        p.setFont(font_main)
        p.drawText(120, 25, "7次")
        
        # 比较
        p.setPen(QtGui.QColor("#27ae60"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(170, 25, "↓ 比昨天 -2次")
        
        # 圆点
        dot_y = 50
        dot_size = 8
        spacing = 15
        start_x = 20
        
        # 5绿 2橙
        colors = ["#27ae60"]*5 + ["#f39c12"]*2 + ["#bdc3c7"]*0
        # 显示7个圆点 (5绿2橙) -> total 7
        # 设计图说: ●●●●●○○ (5实2空? 描述是 5绿2橙)
        # 照着 "5绿2橙" 做
        
        for i, col_code in enumerate(colors):
            p.setBrush(QtGui.QColor(col_code))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(start_x + i*spacing, dot_y, dot_size, dot_size)

class Card3_Flow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 标题
        p.setPen(QtGui.QColor("#7f8c8d"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "⚡ 最长心流时段")
        
        # 内容
        p.setPen(QtGui.QColor("#2c3e50"))
        p.setFont(QtGui.QFont("Noto Sans SC", 12, QtGui.QFont.Bold))
        p.drawText(20, 50, "92分钟")
        p.setPen(QtGui.QColor("#95a5a6"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(100, 50, "（约1.5小时） 9:30-11:02")
        
        # 时间轴
        line_y = 75
        margin_x = 20
        w = self.width() - margin_x * 2
        
        # 轴线
        p.setPen(QtGui.QPen(QtGui.QColor("#ecf0f1"), 1))
        p.drawLine(margin_x, line_y, margin_x + w, line_y)
        
        # 刻度
        times = ["00:00", "06:00", "12:00", "18:00", "23:59"]
        p.setPen(QtGui.QColor("#bdc3c7"))
        p.setFont(QtGui.QFont("Arial", 7))
        for i, t in enumerate(times):
            x = margin_x + (w * i / (len(times)-1))
            p.drawText(int(x - 10), int(line_y - 5), t)
            
        # 高亮段 9:30 - 11:02
        # 假设 0-24h映射到 w
        start_min = 9*60 + 30
        end_min = 11*60 + 2
        total_min = 24*60
        
        x1 = margin_x + (start_min / total_min) * w
        x2 = margin_x + (end_min / total_min) * w
        
        p.setBrush(QtGui.QColor("#3498db"))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(QtCore.QRectF(x1, line_y - 4, x2-x1, 8))

class Card4_Rest(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 标题
        p.setPen(QtGui.QColor("#7f8c8d"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "🛋️ 休息达标率")
        
        # 内容
        p.setPen(QtGui.QColor("#2c3e50"))
        p.setFont(QtGui.QFont("Noto Sans SC", 16, QtGui.QFont.Bold))
        p.drawText(120, 25, "85%")
        
        # 星星
        # ★★★★☆
        star_size = 16
        spacing = 20
        start_x = 20
        y = 45
        
        font_star = QtGui.QFont("Segoe UI Emoji", 14) # Or similar
        p.setFont(font_star)
        
        for i in range(5):
            if i < 4:
                p.setPen(QtGui.QColor("#f1c40f")) # Gold
                txt = "★"
            else:
                p.setPen(QtGui.QColor("#bdc3c7")) # Silver
                txt = "☆" # Or solid grey star
                
            p.drawText(start_x + i*spacing, y + star_size, txt)

# --- 主窗口 ---
class SimpleDailyReport(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(480, 600)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.drag_start_pos = None
        
        # 阴影边距
        self.shadow_margin = 20
        
        # 主布局
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(self.shadow_margin, self.shadow_margin, self.shadow_margin, self.shadow_margin)
        
        # 卡片容器
        self.card_widget = QtWidgets.QWidget()
        self.card_widget.setObjectName("CardWidget")
        self.card_widget.setStyleSheet("""
            QWidget#CardWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)
        
        # 阴影
        shadow = QtWidgets.QGraphicsDropShadowEffect(self.card_widget)
        shadow.setBlurRadius(20)
        shadow.setColor(QtGui.QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.card_widget.setGraphicsEffect(shadow)
        
        self.main_layout.addWidget(self.card_widget)
        
        # 内容布局
        content_layout = QtWidgets.QVBoxLayout(self.card_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 1. 标题区
        title_box = QtWidgets.QWidget()
        title_box.setFixedHeight(100)
        tb_layout = QtWidgets.QVBoxLayout(title_box)
        tb_layout.setContentsMargins(25, 25, 25, 10)
        tb_layout.setSpacing(5)
        
        lbl_t1 = QtWidgets.QLabel("今天又是努力的一天呢！")
        lbl_t1.setStyleSheet("color: #2c3e50; font-family: 'Noto Sans SC'; font-size: 20px; font-weight: bold;")
        lbl_t2 = QtWidgets.QLabel("来看看你的进步足迹吧~")
        lbl_t2.setStyleSheet("color: #7f8c8d; font-family: 'Noto Sans SC'; font-size: 14px;")
        
        # 标题动画: 淡入
        self.title_opacity = QtWidgets.QGraphicsOpacityEffect(title_box)
        title_box.setGraphicsEffect(self.title_opacity)
        self.title_opacity.setOpacity(0)
        
        self.anim_title = QtCore.QPropertyAnimation(self.title_opacity, b"opacity")
        self.anim_title.setDuration(300)
        self.anim_title.setStartValue(0)
        self.anim_title.setEndValue(1)
        self.anim_title.start()
        
        tb_layout.addWidget(lbl_t1)
        tb_layout.addWidget(lbl_t2)
        content_layout.addWidget(title_box)
        
        # 2. 数据卡片列表
        self.cards_container = QtWidgets.QWidget()
        cc_layout = QtWidgets.QVBoxLayout(self.cards_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)
        
        # 添加分隔线辅助函数
        def add_line():
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #f0f0f0; border: none;")
            cc_layout.addWidget(line)
            
        # 卡片1
        self.c1 = Card1_Focus()
        cc_layout.addWidget(self.c1)
        add_line()
        
        # 文案框1
        self.msg1 = self.create_msg_box("比昨天多出30分钟！进步看得见！", "#3498db")
        cc_layout.addWidget(self.msg1)
        add_line()
        
        # 卡片2
        self.c2 = Card2_Distract()
        cc_layout.addWidget(self.c2)
        add_line()
        
        # 文案框2
        self.msg2 = self.create_msg_box("每次提醒后你都快速调整，自控力在增强哦！", "#27ae60")
        cc_layout.addWidget(self.msg2)
        add_line()
        
        # 卡片3
        self.c3 = Card3_Flow()
        cc_layout.addWidget(self.c3)
        add_line()
        
        # 卡片4
        self.c4 = Card4_Rest()
        cc_layout.addWidget(self.c4)
        
        content_layout.addWidget(self.cards_container)
        
        # 列表入场动画: 向上滑入
        self.cards_pos = AnimatedValue(50.0) # offset y
        self.cards_pos.valueChanged.connect(self.update_cards_pos)
        self.cards_pos.animate_to(0, 400, 100, QtCore.QEasingCurve.OutQuad)
        
        # 3. 底部
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(80)
        f_layout = QtWidgets.QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 10, 20, 20)
        
        btn1 = QtWidgets.QPushButton("查看时间轴")
        btn2 = QtWidgets.QPushButton("导出图片")
        
        for btn in [btn1, btn2]:
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    color: #3498db;
                    background: transparent;
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(52, 152, 219, 0.1);
                    border-radius: 5px;
                }
            """)
            
        f_layout.addWidget(btn1)
        f_layout.addStretch()
        f_layout.addWidget(btn2)
        
        content_layout.addWidget(footer)
        content_layout.addStretch()
        
        # 窗口入场动画
        self.start_entrance_anim()

    def create_msg_box(self, text, color_code):
        w = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(w)
        l.setContentsMargins(20, 5, 20, 5)
        
        lbl = QtWidgets.QLabel(text)
        lbl.setWordWrap(True)
        # 背景色 rgba of color_code 0.05
        c = QtGui.QColor(color_code)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.05)"
        
        lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                border-left: 3px solid {color_code};
                padding: 8px;
                color: #555;
                font-size: 12px;
            }}
        """)
        l.addWidget(lbl)
        return w

    def update_cards_pos(self, val):
        self.cards_container.setContentsMargins(0, int(val), 0, 0)

    def start_entrance_anim(self):
        # Scale 0.95 -> 1.0
        self.anim_geo = QtCore.QPropertyAnimation(self, b"geometry")
        # Geometry animation is tricky because we need to keep center
        # Instead, let's just animate opacity and maybe slight movement?
        # User asked for Scale 0.95->1.0. This is hard on a frameless window without a container.
        # Let's do Opacity 0->1
        
        self.window_opacity = 0.0
        self.anim_op = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.anim_op.setDuration(300)
        self.anim_op.setStartValue(0.0)
        self.anim_op.setEndValue(1.0)
        self.anim_op.start()
        
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            self.drag_pos = pos - self.frameGeometry().topLeft()
            self.drag_start_pos = pos
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos is not None and event.button() == QtCore.Qt.LeftButton:
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            drag_distance = (pos - self.drag_start_pos).manhattanLength()
            if drag_distance < QtWidgets.QApplication.startDragDistance():
                self.clicked.emit()
            self.drag_start_pos = None
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            self.move(pos - self.drag_pos)
            event.accept()

def show_simple_daily():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        
    window = SimpleDailyReport()
    window.show()
    
    if not QtWidgets.QApplication.instance():
        if hasattr(app, 'exec'):
            sys.exit(app.exec())
        else:
            sys.exit(app.exec_())
    else:
        if hasattr(app, 'exec'):
            app.exec()
        else:
            app.exec_()

if __name__ == "__main__":
    show_simple_daily()
