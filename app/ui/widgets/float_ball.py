
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
    清新森林单色悬浮球 (v2.0 - 水滴晶体版)
    - 视觉：水滴晶体 (52x52px, 清新绿 #66BB6A)
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
        self._is_destroying = False
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
        self._opacity_level = 1.0 # 基础透明度 (改为不透明)
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

        # 使用定时器延迟初始化位置，以应对高DPI缩放或窗口初始化未完成的问题
        QtCore.QTimer.singleShot(100, self._init_position)

    def _init_position(self):
        """初始化位置到屏幕右下角"""
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            # 使用 geometry() 而不是 availableGeometry() 来获取包括任务栏在内的完整屏幕尺寸
            # 然后手动计算避开任务栏的大致位置，或者直接贴边
            # 这里我们尝试更激进的计算方式
            screen_geo = screen.availableGeometry()
            
            # 获取实际的 DPI 缩放因子
            # ratio = screen.devicePixelRatio() 
            # 注意：move() 使用的是逻辑坐标，理论上不需要手动乘除 ratio，
            # 但如果 Application 没有开启 AA_EnableHighDpiScaling，可能会有问题。
            # 这里先假设坐标系是正确的逻辑坐标。
            
            # 距离右边 50px
            x = screen_geo.right() - self.width() - 50
            
            # 距离底部 100px (加大一点以防被任务栏遮挡)
            y = screen_geo.bottom() - self.height() - 100
            
            self.move(int(x), int(y))
            print(f"FloatBall init pos: {x}, {y}, Screen: {screen_geo}") # 调试信息

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
                color: rgba(27, 94, 32, 0.95);
                background-color: rgba(232, 245, 233, 0.9);
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
        
    def closeEvent(self, event):
        """窗口关闭时设置销毁标志，停止所有动画"""
        self._is_destroying = True
        
        # 停止所有动画
        if hasattr(self, 'breath_anim'):
            self.breath_anim.stop()
        if hasattr(self, 'rotation_anim'):
            self.rotation_anim.stop()
        if hasattr(self, 'scale_anim'):
            self.scale_anim.stop()
        if hasattr(self, 'opacity_anim'):
            self.opacity_anim.stop()
        
        # 停止定时器
        if hasattr(self, 'ring_timer'):
            self.ring_timer.stop()
        
        # 调用父类方法
        super().closeEvent(event)

    # ================= 属性定义 (用于动画) =================
    
    @Property(float)
    def rotation_angle(self):
        return self._rotation_angle
    
    @rotation_angle.setter
    def rotation_angle(self, angle):
        if self._is_destroying:  # ← 添加这行检查
            return
        self._rotation_angle = angle
        self.update()
        
    @Property(float)
    def scale_factor(self):
        return self._scale_factor
    
    @scale_factor.setter  
    def scale_factor(self, factor):
        if self._is_destroying:  # ← 添加这行检查
            return
        self._scale_factor = factor
        self.update()
        
    @Property(float)
    def opacity_level(self):
        return self._opacity_level
    
    @opacity_level.setter
    def opacity_level(self, val):
        if self._is_destroying:  # ← 添加这行检查
            return
        self._opacity_level = val
        self.update()
        
    @Property(float)
    def breath_offset(self):
        return self._breath_offset
        
    @breath_offset.setter
    def breath_offset(self, val):
        if self._is_destroying:  # ← 添加这行检查
            return
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
        
        # --- 1. 绘制主体 (水晶球) ---
        # 径向渐变模拟球体光感
        # 焦点稍微偏左上 (-0.3, -0.3)
        radial_grad = QtGui.QRadialGradient(radius * -0.3, radius * -0.3, radius * 1.5)
        
        # 颜色配置 (清新绿单色系)
        # 核心高光: 白色
        # 主体: 清新绿 (#66BB6A) -> rgb(102, 187, 106)
        # 阴影: 深绿
        
        base_color = QtGui.QColor(102, 187, 106) # #66BB6A
        base_color.setAlphaF(self._opacity_level)
        
        highlight = QtGui.QColor(255, 255, 255, int(255 * 0.9))
        shadow = QtGui.QColor(56, 142, 60, int(255 * 0.8)) # #388E3C
        
        radial_grad.setColorAt(0.0, highlight)
        radial_grad.setColorAt(0.2, base_color)
        radial_grad.setColorAt(1.0, shadow)
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(radial_grad)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # --- 2. 绘制高光 (Glossy) ---
        # 顶部反光
        gloss_grad = QtGui.QLinearGradient(0, -radius, 0, 0)
        gloss_grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 220))
        gloss_grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        
        painter.setBrush(gloss_grad)
        # 稍微缩小的椭圆作为高光区域
        painter.drawEllipse(QtCore.QPointF(0, -radius * 0.5), radius * 0.7, radius * 0.4)
        
        # --- 3. 绘制边缘光 (Rim Light) ---
        # 底部边缘微发光，增加立体感
        border_pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 100), 1.5)
        painter.setPen(border_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius - 1, radius - 1)
        
        # 外部柔光晕 (呼吸效果的一部分)
        # if self._state == 'focus':
        #     glow_color = QtGui.QColor(102, 187, 106)
        #     glow_color.setAlphaF(0.3 + self._breath_offset) # 呼吸变化
            
        #     painter.setPen(QtCore.Qt.NoPen)
        #     painter.setBrush(glow_color)
        #     # 绘制一个稍大的同心圆作为光晕
        #     painter.drawEllipse(QtCore.QPointF(0, 0), radius + 4, radius + 4)
            
        # 恢复画笔绘制主体边框
        border_pen = QtGui.QPen(QtGui.QColor(102, 187, 106, 50), 1)
        painter.setPen(border_pen)
        
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # --- 5. 绘制进度环 (悬停时) ---
        # if self._show_ring:
        #     self._draw_progress_ring(painter, radius + 3)

    def _draw_progress_ring(self, painter, radius):
        """绘制微进度环"""
        # 背景环
        pen_bg = QtGui.QPen(QtGui.QColor(102, 187, 106, 80), 2) # Green bg
        painter.setPen(pen_bg)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPointF(0, 0), radius, radius)
        
        # 进度环 (100% Green)
        if self._progress > 0:
            pen_fill = QtGui.QPen(QtGui.QColor(102, 187, 106, 255), 2) # Green fill
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
        target_alpha = 1.0
        
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
        self.opacity_anim.setEndValue(1.0)
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
        """鼠标按下事件"""
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
