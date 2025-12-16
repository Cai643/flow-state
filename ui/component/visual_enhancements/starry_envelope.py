import random
import math
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

# 导入统一主题
try:
    from ui.component.report.report_theme import theme as MorandiTheme
except ImportError:
    try:
        from ..report.report_theme import theme as MorandiTheme
    except ImportError:
        # Fallback if relative import fails
        from ui.component.report.report_theme import theme as MorandiTheme

class StarryEnvelopeWidget(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(370, 250) # 界面稍微调大
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # 状态变量
        self.scale_factor = 1.0
        self.rotation = 0.0
        self.opacity = 1.0
        self.disappearing = False
        
        self.border_alpha = 102 # 40%
        self.border_width = 3.0
        self.border_color = QtGui.QColor(MorandiTheme.COLOR_BORDER) # Light Green
        self.border_color.setAlpha(self.border_alpha)
        self.grad_start = QtGui.QColor(165, 214, 167)
        self.grad_end = QtGui.QColor(200, 230, 201)
        
        # 星星数据
        self.stars = self._init_stars()
        self.shooting_star = None
        
        # 动画定时器 (星星)
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self.update_animations)
        self.anim_timer.start(50) # 20 FPS
        
        # 流星定时器
        QtCore.QTimer.singleShot(2000, self.spawn_shooting_star)
        
        # 阴影效果
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QtGui.QColor(0, 0, 0, 128))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)

    def _init_stars(self):
        stars = []
        # 主星 (3颗) - 针对 280x180 尺寸调整
        stars.append({'type': 'main', 'x': 25, 'y': 25, 'size': 2, 'delay': 0})
        stars.append({'type': 'main', 'x': 255, 'y': 45, 'size': 2, 'delay': 0.5})
        stars.append({'type': 'main', 'x': 230, 'y': 155, 'size': 2, 'delay': 1.0})
        
        # 背景星星 (5颗)
        for _ in range(5):
             while True:
                 x = random.randint(10, 270)
                 y = random.randint(10, 170)
                 # 避开文字中心区域 (调整)
                 if not (50 < x < 230 and 50 < y < 130):
                     break
             stars.append({'type': 'bg', 'x': x, 'y': y, 'size': 1, 'delay': random.random()*5})
        return stars

    def spawn_shooting_star(self):
        # 从左上到右下 (约 45 度) - 针对 280x180 尺寸调整
        self.shooting_star = {
            'start_x': 25, 'start_y': 25, 
            'end_x': 255, 'end_y': 155, 
            'progress': 0.0
        }

    def update_animations(self):
        if self.disappearing:
            return

        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0
        
        # 更新星星
        for star in self.stars:
            if star['type'] == 'main':
                # 3秒周期: 0.8 -> 1 -> 0.8
                t = (current_time + star['delay']) % 3.0
                norm = t / 1.5 if t < 1.5 else (3.0 - t) / 1.5
                star['alpha'] = 204 + (51 * norm) # 0.8 到 1.0
                star['current_size'] = star['size'] * (1.0 + 0.2 * norm)
            else:
                # 8秒周期: 0.1 -> 0.2 -> 0.1
                t = (current_time + star['delay']) % 8.0
                norm = t / 4.0 if t < 4.0 else (8.0 - t) / 4.0
                star['alpha'] = 25 + (26 * norm) # 约 10% 到 20%
                star['current_size'] = star['size']
                
        # 更新流星
        if self.shooting_star:
            self.shooting_star['progress'] += 0.0125 # 约 4秒完成 (0.0125 * 20fps * 4s = 1.0)
            if self.shooting_star['progress'] >= 1.0:
                self.shooting_star = None
                
        self.update()

    def set_gradient(self, start_color: str, end_color: str):
        self.grad_start = QtGui.QColor(start_color)
        self.grad_end = QtGui.QColor(end_color)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setOpacity(self.opacity)
        
        # 处理变换
        cx, cy = self.width() / 2, self.height() / 2
        painter.translate(cx, cy)
        painter.scale(self.scale_factor, self.scale_factor)
        painter.rotate(self.rotation)
        painter.translate(-cx, -cy)
        
        rect = self.rect()
        
        gradient = QtGui.QLinearGradient(0, 0, 0, 200)
        gradient.setColorAt(0, self.grad_start)
        gradient.setColorAt(1, self.grad_end)
        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        # 2. 星星
        for star in self.stars:
            color = QtGui.QColor(255, 255, 255)
            color.setAlpha(int(star.get('alpha', 255)))
            painter.setBrush(color)
            s = star.get('current_size', 1)
            painter.drawEllipse(QtCore.QPointF(star['x'], star['y']), s/2, s/2)
            
        # 3. 流星
        if self.shooting_star:
            p = self.shooting_star['progress']
            # 淡入淡出: 0 -> 80% -> 0
            if p < 0.5:
                alpha = (p / 0.5) * 204
            else:
                alpha = ((1.0 - p) / 0.5) * 204
                
            pen = QtGui.QPen(QtGui.QColor(255, 215, 0, int(alpha)), 1)
            painter.setPen(pen)
            
            sx = self.shooting_star['start_x'] + (self.shooting_star['end_x'] - self.shooting_star['start_x']) * p
            sy = self.shooting_star['start_y'] + (self.shooting_star['end_y'] - self.shooting_star['start_y']) * p
            # 绘制轨迹
            painter.drawLine(QtCore.QPointF(sx, sy), QtCore.QPointF(sx-3, sy-3))

        # 4. 文本
        # 主标题 (位置针对新尺寸调整)
        painter.setPen(QtGui.QColor("#5D4037"))
        font = QtGui.QFont("Noto Sans SC", 14, QtGui.QFont.Bold)
        font.setPixelSize(18)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.5)
        painter.setFont(font)
        
        # 文字发光 (通过先绘制阴影模拟)
        painter.save()
        glow_color = QtGui.QColor(255, 215, 0, 76)
        painter.setPen(glow_color)
        painter.translate(0, 0) # 发光无偏移
        painter.restore()
        
        painter.drawText(rect.adjusted(0, 45, 0, 0), QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, "一封来自森林的信")
        
        # 副标题 (位置针对新尺寸调整)
        painter.setPen(QtGui.QColor(27, 94, 32, 204))
        font_sub = QtGui.QFont("Noto Sans SC")
        font_sub.setPixelSize(12)
        painter.setFont(font_sub)
        painter.drawText(rect.adjusted(0, 75, 0, 0), QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, "点开有惊喜哟！")
        
        # 5. Emoji 装饰 (位置针对新尺寸调整)
        painter.setPen(QtGui.QColor("#F9A825"))
        font_emoji = QtGui.QFont("Segoe UI Emoji")
        font_emoji.setPixelSize(20)
        painter.setFont(font_emoji)
        
        t = (QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0) % 2.0
        # 闪烁: 0.8 -> 1 -> 0.8
        e_norm = t if t < 1 else 2 - t
        e_alpha = 204 + (51 * e_norm)
        
        painter.setOpacity(self.opacity * (e_alpha / 255.0))
        painter.drawText(rect.adjusted(0, 15, 0, 0), QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, "✨")
        painter.setOpacity(self.opacity) # 恢复

        # 6. 边框
        pen = QtGui.QPen(self.border_color, self.border_width)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 8, 8)

    def enterEvent(self, event):
        if not self.disappearing:
            self.scale_factor = 1.02
            self.border_alpha = 153 # 60%
            self.border_color.setAlpha(153)
            self.shadow.setBlurRadius(24)
            self.shadow.setOffset(0, 6)
            self.update()

    def leaveEvent(self, event):
        if not self.disappearing:
            self.scale_factor = 1.0
            self.border_alpha = 102 # 40%
            self.border_color.setAlpha(102)
            self.shadow.setBlurRadius(20)
            self.shadow.setOffset(0, 4)
            self.update()

    def mousePressEvent(self, event):
        if not self.disappearing:
            self.scale_factor = 0.98
            self.border_color = QtGui.QColor(MorandiTheme.COLOR_ACCENT_DARK)
            self.border_width = 4.0
            self.shadow.setBlurRadius(8)
            self.shadow.setOffset(0, 2)
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if not self.disappearing:
            self.disappearing = True
            
            # 停止星星动画定时器，减少 CPU 占用
            if hasattr(self, 'anim_timer'):
                self.anim_timer.stop()
                
            # 移除阴影效果，极大提升动画性能
            # 阴影在每帧动画时都需要重绘，是卡顿的主要原因
            self.setGraphicsEffect(None)
            
            # 开始消失动画 - 优化参数
            # 16ms = 60 FPS
            self.disappear_timer = QtCore.QTimer(self)
            self.disappear_progress = 0.0
            self.disappear_timer.timeout.connect(self.update_disappear)
            self.disappear_timer.start(16)
        event.accept()

    def update_disappear(self):
        # 0.08 * 12 frames ~= 200ms duration
        self.disappear_progress += 0.08
        if self.disappear_progress >= 1.0:
            self.disappear_timer.stop()
            self.clicked.emit()
            self.hide()
        else:
            self.scale_factor = 0.98 * (1.0 - 0.2 * self.disappear_progress)
            self.opacity = 1.0 - self.disappear_progress
            self.rotation = 5.0 * self.disappear_progress
            self.update()


# --- 动画辅助类 ---

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

# --- 容器组件 ---

class ReportEnvelopeContainer(QtWidgets.QWidget):
    """
    通用报表信封容器
    封装了信封拆解动画和内容展示逻辑
    """
    stateChanged = Signal(bool)  # True=展开, False=折叠

    def __init__(self, expanded_height=900, parent=None):
        super().__init__(parent)
        self.expanded_height = expanded_height
        self.collapsed_height = 280
        self.is_collapsed = True
        self.animation_in_progress = False
        
        # 布局
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 内容容器
        self.content_container = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 信封组件
        self.toggle_button = StarryEnvelopeWidget()
        self.toggle_button.clicked.connect(self.expand)
        
        # 信封容器 (居中)
        self.envelope_container = QtWidgets.QWidget()
        self.envelope_layout = QtWidgets.QHBoxLayout(self.envelope_container)
        self.envelope_layout.setContentsMargins(0, 10, 0, 10)
        self.envelope_layout.addStretch()
        self.envelope_layout.addWidget(self.toggle_button)
        self.envelope_layout.addStretch()

        self.main_layout.addWidget(self.envelope_container)
        self.main_layout.addWidget(self.content_container)

        # 动画
        self.height_anim = AnimatedValue(self.collapsed_height)
        self.height_anim.valueChanged.connect(self._update_height)
        
        self.content_opacity = AnimatedValue(1.0)
        self.content_opacity.valueChanged.connect(self._update_content_opacity)

        # 初始状态
        self.setFixedHeight(self.collapsed_height)
        self.content_container.hide()
        self.envelope_container.show()

    def set_content(self, widget: QtWidgets.QWidget):
        """设置展开后显示的内容"""
        # 清除旧内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.content_layout.addWidget(widget)
        # 如果当前是折叠状态，隐藏内容
        if self.is_collapsed:
            widget.hide()
        else:
            widget.show()

    def expand(self):
        """展开动画"""
        if not self.is_collapsed or self.animation_in_progress:
            return
            
        self.animation_in_progress = True
        self.is_collapsed = False
        
        # 1. 隐藏信封 (信封自己会播放消失动画，这里只需要处理容器逻辑)
        # 注意：StarryEnvelopeWidget.clicked 信号是在消失动画完成后触发的
        # 所以此时信封已经不可见了（或者正在变得不可见）
        
        self.envelope_container.hide()
        
        # 2. 展开高度 - 减少动画时间 (500 -> 300)
        self.height_anim.animate_to(
            self.expanded_height, 
            300, 
            0, 
            QtCore.QEasingCurve.OutQuad # 使用更轻快的曲线
        )
        
        # 3. 显示内容并淡入
        self.content_container.show()
        widget = self.content_layout.itemAt(0).widget()
        if widget:
            widget.show()
            
        self.content_opacity.value = 0.0
        # 减少延迟 (250 -> 50) 和动画时间 (200 -> 150)
        QtCore.QTimer.singleShot(50, lambda: self.content_opacity.animate_to(
            1.0, 
            150, 
            0, 
            QtCore.QEasingCurve.OutQuad
        ))
        
        self.stateChanged.emit(True)

    def _update_height(self, height: float):
        self.setFixedHeight(int(height))
        if abs(height - self.expanded_height) < 1:
            self.animation_in_progress = False

    def _update_content_opacity(self, opacity: float):
        effect = QtWidgets.QGraphicsOpacityEffect()
        effect.setOpacity(opacity)
        self.content_container.setGraphicsEffect(effect)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    # 创建一个暗色背景的测试窗口
    test_window = QtWidgets.QWidget()
    test_window.setStyleSheet("background-color: #333333;")
    test_window.setFixedSize(400, 300)
    layout = QtWidgets.QVBoxLayout(test_window)
    layout.setAlignment(QtCore.Qt.AlignCenter)
    
    # 创建信封组件
    envelope = StarryEnvelopeWidget()
    layout.addWidget(envelope)
    
    def on_envelope_clicked():
        print("Envelope Clicked!")
        # 重置信封状态以便再次点击
        QtCore.QTimer.singleShot(1000, lambda: envelope.show())
        envelope.opacity = 1.0
        envelope.scale_factor = 1.0
        envelope.disappearing = False
        envelope.rotation = 0.0
        
    envelope.clicked.connect(on_envelope_clicked)
    
    test_window.show()
    sys.exit(app.exec())
