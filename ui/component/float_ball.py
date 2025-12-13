
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

import math

class SuspensionBall(QtWidgets.QWidget):
    """
    莫兰迪蓝单色悬浮球 (v2.0 - 水滴晶体版)
    - 视觉：水滴晶体 (52x52px, 莫兰迪蓝 #a8d8ea)
    - 交互：呼吸、微旋转、缩放反馈
    - 信息：微文字、微进度环
    """
    
    # 信号定义
    clicked = Signal()
    double_clicked = Signal()
    entered = Signal()
    left = Signal()
    positionChanged = Signal(QtCore.QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. 窗口属性设置
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |  # 无边框
            QtCore.Qt.Tool |                 # 工具窗口
            QtCore.Qt.WindowStaysOnTopHint   # 始终置顶
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground) # 背景透明
        self.setMouseTracking(True)
        
        # 尺寸定义
        self._ball_size = 43  # 小球直径 (原尺寸)
        self._margin = 8      # 预留给阴影和缩放的边距 (相应调小)
        self.setFixedSize(self._ball_size + self._margin * 2, self._ball_size + self._margin * 2)
        
        # 2. 状态与属性
        self._state = 'focus'  # 当前状态
        self._hovering = False
        self._dragging = False
        self._drag_start_pos = QtCore.QPoint()
        
        # 动画属性
        self._rotation_angle = 0.0
        self._scale_factor = 1.0
        self._opacity_level = 0.85 # 基础透明度
        self._breath_offset = 0.0  # 呼吸叠加值
        
        # 数据属性
        self._progress = 0.0 # 0.0 - 1.0 (用于进度环)
        self._show_ring = False
        
        # 3. 初始化子组件（微文字）
        self._setup_ui()
        
        # 4. 初始化动画系统
        self._setup_animations()
        
        # 初始状态
        self.update_state('focus')

    def _setup_ui(self):
        # 微文字标签 (默认隐藏，悬停显示)
        self.micro_label = QtWidgets.QLabel(self)
        self.micro_label.setAlignment(QtCore.Qt.AlignCenter)
        self.micro_label.hide()
        
        # 样式表
        self.micro_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei";
                font-size: 10px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.95);
                background-color: rgba(168, 216, 234, 0.4);
                border-radius: 4px;
                padding: 1px 3px;
            }
        """)
        # 调整大小和位置 (位于球体中心偏下)
        self.micro_label.adjustSize()
        self._update_label_pos()

    def _update_label_pos(self):
        # 居中放置
        lw = self.micro_label.width()
        lh = self.micro_label.height()
        cx = self.width() // 2
        cy = self.height() // 2
        # 稍微偏下一点
        self.micro_label.move(cx - lw // 2, cy + 10)

    def _setup_animations(self):
        # --- A. 呼吸动画 (Opacity) ---
        self.breath_anim = QtCore.QPropertyAnimation(self, b"breath_offset", self)
        self.breath_anim.setLoopCount(-1) # 无限循环
        
        # --- B. 旋转动画 (Rotation) ---
        self.rotation_anim = QtCore.QPropertyAnimation(self, b"rotation_angle", self)
        self.rotation_anim.setLoopCount(-1)
        
        # --- C. 缩放动画 (Scale) ---
        self.scale_anim = QtCore.QPropertyAnimation(self, b"scale_factor", self)
        
        # --- D. 基础透明度动画 (切换状态时用) ---
        self.opacity_anim = QtCore.QPropertyAnimation(self, b"opacity_level", self)
        
        # --- E. 进度环显示延迟 ---
        self.ring_timer = QtCore.QTimer(self)
        self.ring_timer.setSingleShot(True)
        self.ring_timer.setInterval(50)
        self.ring_timer.timeout.connect(self._show_ring_visuals)

    # ================= 属性定义 (用于动画) =================
    
    @Property(float)
    def rotation_angle(self):
        return self._rotation_angle
    
    @rotation_angle.setter
    def rotation_angle(self, angle):
        self._rotation_angle = angle
        self.update() # 重绘
        
    @Property(float)
    def scale_factor(self):
        return self._scale_factor
    
    @scale_factor.setter
    def scale_factor(self, factor):
        self._scale_factor = factor
        self.update()
        
    @Property(float)
    def opacity_level(self):
        return self._opacity_level
    
    @opacity_level.setter
    def opacity_level(self, val):
        self._opacity_level = val
        self.update()
        
    @Property(float)
    def breath_offset(self):
        return self._breath_offset
        
    @breath_offset.setter
    def breath_offset(self, val):
        self._breath_offset = val
        self.update()

    # ================= 核心绘制逻辑 =================
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        
        # 1. 坐标系变换：移到中心，旋转，缩放
        cx = self.width() / 2
        cy = self.height() / 2
        
        painter.translate(cx, cy)
        painter.rotate(self._rotation_angle)
        painter.scale(self._scale_factor, self._scale_factor)
        
        # 实际绘制半径 (52px / 2 = 26px)
        radius = self._ball_size / 2
        
        # 计算当前总透明度 (基础 + 呼吸)
        # 限制在 0.1 - 1.0 之间
        current_alpha = max(0.1, min(1.0, self._opacity_level + self._breath_offset))
        
        # --- 2. 绘制外阴影 (极淡) ---
        # 模拟 box-shadow: 0 2px 8px rgba(0,0,0,0.08)
        # 简单起见，画一个稍大的半透明圆
        painter.setPen(QtCore.Qt.NoPen)
        shadow_color = QtGui.QColor(0, 0, 0, int(255 * 0.08))
        painter.setBrush(shadow_color)
        painter.drawEllipse(QtCore.QPointF(0, 2), radius + 2, radius + 2)
        
        # --- 3. 绘制主体 (毛玻璃水滴) ---
        # background: qradialgradient(...)
        # 莫兰迪蓝基色: rgba(168, 216, 234) -> #a8d8ea
        
        gradient = QtGui.QRadialGradient(0, 0, radius, -radius * 0.3, -radius * 0.3)
        # stop:0 rgba(168, 216, 234, 0.9)
        c1 = QtGui.QColor(168, 216, 234)
        c1.setAlphaF(current_alpha * 0.95) # 稍微调整系数
        
        # stop:1 rgba(127, 179, 232, 0.6)
        c2 = QtGui.QColor(127, 179, 232)
        c2.setAlphaF(current_alpha * 0.7)
        
        gradient.setColorAt(0.0, c1)
        gradient.setColorAt(1.0, c2)
        
        painter.setBrush(gradient)
        
        # 边框: 2px solid rgba(168, 216, 234, 0.9)
        border_pen = QtGui.QPen(QtGui.QColor(168, 216, 234, int(255 * 0.9)), 2)
        painter.setPen(border_pen)
        
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # --- 4. 绘制内阴影 (凹陷感) ---
        # 模拟 box-shadow: inset 0 1px 2px rgba(0,0,0,0.1)
        # 在顶部绘制一个半月形或渐变来模拟
        # 这里用一个简单的线性渐变覆盖层
        inner_shadow = QtGui.QLinearGradient(0, -radius, 0, radius)
        inner_shadow.setColorAt(0.0, QtGui.QColor(0, 0, 0, 20))
        inner_shadow.setColorAt(0.2, QtGui.QColor(0, 0, 0, 0))
        inner_shadow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(inner_shadow)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # --- 5. 绘制进度环 (悬停时) ---
        if self._show_ring:
            self._draw_progress_ring(painter, radius + 3)

    def _draw_progress_ring(self, painter, radius):
        """绘制微进度环"""
        # 背景环
        pen_bg = QtGui.QPen(QtGui.QColor(168, 216, 234, 80), 2)
        painter.setPen(pen_bg)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # 进度环 (100% 蓝)
        if self._progress > 0:
            pen_fill = QtGui.QPen(QtGui.QColor(168, 216, 234, 255), 2)
            pen_fill.setCapStyle(QtCore.Qt.RoundCap)
            painter.setPen(pen_fill)
            
            # drawArc 使用 1/16 度为单位
            # 12点钟方向开始 (90度), 逆时针画? 或者是顺时针 - spanAngle
            # Qt drawArc: 0度是3点钟，正值逆时针。
            # 我们想要从12点钟开始(90度)，顺时针画(-span)
            start_angle = 90 * 16
            span_angle = -self._progress * 360 * 16
            
            rect = QtCore.QRectF(-radius, -radius, radius*2, radius*2)
            painter.drawArc(rect, start_angle, int(span_angle))

    # ================= 状态管理 =================
    
    def update_state(self, state):
        """
        更新小球状态
        state: 'focus', 'distract_lite', 'distract_heavy', 'rest', 'overwork'
        """
        self._state = state
        
        # 1. 设置基础透明度
        target_alpha = {
            'focus': 0.85,
            'distract_lite': 0.75,
            'distract_heavy': 0.65,
            'rest': 0.95,
            'overwork': 0.55
        }.get(state, 0.85)
        
        # 平滑过渡透明度
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(300)
        self.opacity_anim.setEndValue(target_alpha)
        self.opacity_anim.start()
        
        # 2. 设置呼吸节奏
        breath_duration = {
            'focus': 4000,
            'distract_lite': 3000,
            'distract_heavy': 2000,
            'rest': 6000,
            'overwork': 1000
        }.get(state, 4000)
        
        self.breath_anim.stop()
        self.breath_anim.setDuration(breath_duration)
        self.breath_anim.setStartValue(0.0)
        self.breath_anim.setEndValue(0.05) # 呼吸幅度 0.05
        self.breath_anim.setEasingCurve(QtCore.QEasingCurve.SineCurve) # 模拟呼吸曲线
        self.breath_anim.start()
        
        # 3. 设置旋转
        self.rotation_anim.stop()
        if state in ['distract_lite', 'distract_heavy', 'overwork']:
            angle = {
                'distract_lite': 3.0,
                'distract_heavy': 5.0,
                'overwork': 10.0
            }.get(state, 0.0)
            
            duration = {
                'distract_lite': 2000,
                'distract_heavy': 1500,
                'overwork': 800
            }.get(state, 2000)
            
            self.rotation_anim.setDuration(duration)
            self.rotation_anim.setStartValue(-angle)
            self.rotation_anim.setEndValue(angle)
            self.rotation_anim.setEasingCurve(QtCore.QEasingCurve.SineCurve) # 摆动
            self.rotation_anim.start()
        else:
            # 复位旋转
            self._rotation_angle = 0.0
            self.update()

        # 4. 特殊效果：微震动
        if state == 'distract_heavy':
            self._start_micro_shake()

    def _start_micro_shake(self):
        # 简单的震动序列
        offsets = [(1,0), (-1,0), (0,1), (0,-1), (0,0)]
        for i, (dx, dy) in enumerate(offsets):
            QtCore.QTimer.singleShot(i * 50, lambda x=dx, y=dy: self._apply_shake(x, y))
            
    def _apply_shake(self, dx, dy):
        # 这里我们震动整个窗口，或者只震动内容？
        # 震动窗口比较明显
        pos = self.pos()
        self.move(pos.x() + dx, pos.y() + dy)

    def update_data(self, progress=0.0, text=None):
        """更新微信息"""
        self._progress = progress
        if text:
            self.micro_label.setText(text)
            self.micro_label.adjustSize()
            self._update_label_pos()
        self.update()

    # ================= 交互事件 =================
    
    def enterEvent(self, event):
        self._hovering = True
        
        # 悬停动画：放大 + 变清晰
        self.scale_anim.stop()
        self.scale_anim.setDuration(150)
        self.scale_anim.setEndValue(1.05)
        self.scale_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        self.scale_anim.start()
        
        # 提升透明度
        self._prev_opacity = self._opacity_level
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(150)
        self.opacity_anim.setEndValue(0.95)
        self.opacity_anim.start()
        
        # 延迟显示环和文字
        self.ring_timer.start()
        
        self.entered.emit()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovering = False
        
        # 恢复大小
        self.scale_anim.stop()
        self.scale_anim.setDuration(150)
        self.scale_anim.setEndValue(1.0)
        self.scale_anim.start()
        
        # 恢复透明度
        self.opacity_anim.stop()
        self.opacity_anim.setDuration(150)
        self.opacity_anim.setEndValue(self._prev_opacity) # 恢复到状态对应的透明度
        self.opacity_anim.start()
        
        # 隐藏环和文字
        self.ring_timer.stop()
        self._show_ring = False
        self.micro_label.hide()
        self.update()
        
        self.left.emit()
        super().leaveEvent(event)

    def _show_ring_visuals(self):
        if self._hovering:
            self._show_ring = True
            # 如果有文字内容，也显示文字
            if self.micro_label.text():
                self.micro_label.show()
            self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            
            # 点击反馈：缩小
            self.scale_anim.stop()
            self.scale_anim.setDuration(100)
            self.scale_anim.setEndValue(0.95)
            self.scale_anim.setEasingCurve(QtCore.QEasingCurve.OutBack)
            self.scale_anim.start()
            
            self.clicked.emit()
            
    def mouseReleaseEvent(self, event):
        self._dragging = False
        
        # 松开反馈：回弹
        self.scale_anim.stop()
        self.scale_anim.setDuration(100)
        self.scale_anim.setEndValue(1.05 if self._hovering else 1.0)
        self.scale_anim.start()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & QtCore.Qt.LeftButton):
            self.move(event.globalPos() - self._drag_start_pos)
            
            # 拖拽时的动态效果：透明度降低 + 倾斜 (可选)
            # 这里简单实现透明度变化
            # self.setWindowOpacity(0.8) # 也可以

    def moveEvent(self, event):
        self.positionChanged.emit(self.pos())
        super().moveEvent(event)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    # 演示窗口
    ball = SuspensionBall()
    ball.show()
    ball.move(300, 300)
    
    # 模拟数据更新
    ball.update_data(0.75, "32m")
    
    # 模拟状态切换测试
    test_timer = QtCore.QTimer()
    states = ['focus', 'distract_lite', 'distract_heavy', 'rest', 'overwork']
    idx = 0
    
    def switch_state():
        global idx
        s = states[idx % len(states)]
        print(f"Switching to state: {s}")
        ball.update_state(s)
        
        # 模拟不同状态下的微文字
        if s == 'focus':
            ball.update_data(0.8, "Day 7")
        elif s == 'rest':
            ball.update_data(0.0, None) # 休息时不显示
        else:
            ball.update_data(0.3, "12m")
            
        idx += 1
        
    test_timer.timeout.connect(switch_state)
    test_timer.start(5000) # 每5秒切换一次状态
    
    sys.exit(app.exec())
