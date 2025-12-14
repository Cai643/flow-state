"""
交互反馈系统

为用户交互提供即时的视觉反馈，包括悬停、点击、状态反馈等。
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
from typing import Optional, Callable
from .precision_animation_engine import PrecisionAnimationEngine
from .visual_effects_manager import VisualEffectsManager


class InteractionFeedbackSystem(QtCore.QObject):
    """交互反馈系统"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_engine = PrecisionAnimationEngine(self)
        self.effects_manager = VisualEffectsManager(self)
        self._feedback_widgets = {}

    def setup_hover_feedback(self, widget: QtWidgets.QWidget,
                             scale_factor: float = 1.05,
                             shadow_enhancement: bool = True):
        """设置悬停反馈效果"""
        original_cursor = widget.cursor()
        widget.setCursor(QtCore.Qt.PointingHandCursor)

        # 保存原始状态
        original_geometry = widget.geometry()
        original_effect = widget.graphicsEffect()

        def on_enter():
            # 缩放动画
            hover_anim = self.animation_engine.create_hover_animation(
                widget, scale_factor)
            hover_anim.start()

            # 增强阴影效果
            if shadow_enhancement:
                self.effects_manager.apply_card_shadow(
                    widget, blur_radius=20, offset=(0, 6), opacity=0.4
                )

        def on_leave():
            # 恢复原始大小
            restore_anim = self.animation_engine.create_layout_resize_animation(
                widget, original_geometry, 200
            )
            restore_anim.start()

            # 恢复原始阴影
            if shadow_enhancement:
                widget.setGraphicsEffect(original_effect)

        # 安装事件过滤器
        event_filter = HoverEventFilter(on_enter, on_leave)
        widget.installEventFilter(event_filter)

        # 保存引用以防止垃圾回收
        self._feedback_widgets[widget] = event_filter

    def setup_click_feedback(self, widget: QtWidgets.QWidget,
                             with_particles: bool = True,
                             ripple_effect: bool = True):
        """设置点击反馈效果"""
        def on_click(pos: QtCore.QPoint):
            # 按钮按下动画
            press_anim = self.animation_engine.create_button_press_animation(
                widget)
            press_anim.start()

            # 波纹效果
            if ripple_effect:
                self.effects_manager.create_ripple_effect(widget, pos)

            # 粒子效果（如果启用）
            if with_particles:
                self._create_click_particles(widget, pos)

        # 安装点击事件过滤器
        click_filter = ClickEventFilter(on_click)
        widget.installEventFilter(click_filter)

        self._feedback_widgets[widget] = click_filter

    def show_success_feedback(self, widget: QtWidgets.QWidget,
                              message: str = "操作成功！",
                              duration: int = 2000):
        """显示成功状态反馈"""
        self._show_status_feedback(widget, message, '#00FF88', duration)

    def show_error_feedback(self, widget: QtWidgets.QWidget,
                            message: str = "操作失败！",
                            duration: int = 3000):
        """显示错误状态反馈"""
        self._show_status_feedback(widget, message, '#FF6B6B', duration)

    def show_loading_feedback(self, widget: QtWidgets.QWidget,
                              progress: float = -1):
        """显示加载状态反馈"""
        # 创建加载指示器
        loading_widget = LoadingIndicator(widget)
        loading_widget.show()

        if progress >= 0:
            loading_widget.set_progress(progress)
        else:
            loading_widget.start_spinning()

        return loading_widget

    def _show_status_feedback(self, widget: QtWidgets.QWidget,
                              message: str, color: str, duration: int):
        """显示状态反馈消息"""
        # 创建状态提示
        status_label = QtWidgets.QLabel(message, widget)
        status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }}
        """)
        status_label.adjustSize()

        # 定位到组件上方
        pos = QtCore.QPoint(
            widget.width() // 2 - status_label.width() // 2,
            -status_label.height() - 10
        )
        status_label.move(pos)

        # 淡入动画
        fade_in = self.animation_engine.create_fade_in_animation(
            status_label, 300)
        fade_in.start()

        # 定时淡出
        def fade_out_and_remove():
            fade_out = self.animation_engine.create_fade_out_animation(
                status_label, 300)
            fade_out.finished.connect(status_label.deleteLater)
            fade_out.start()

        QtCore.QTimer.singleShot(duration, fade_out_and_remove)
        status_label.show()

    def _create_click_particles(self, widget: QtWidgets.QWidget, pos: QtCore.QPoint):
        """创建点击粒子效果"""
        # 简化的粒子效果
        for i in range(5):
            particle = ClickParticle(widget, pos)
            particle.show()

    def ensure_non_blocking_feedback(self, animation: QtCore.QPropertyAnimation):
        """确保反馈动画不阻塞用户操作"""
        # 设置动画为非阻塞
        animation.setLoopCount(1)

        # 确保动画完成后清理资源
        def cleanup():
            if hasattr(animation, 'target'):
                target = animation.target()
                if target and hasattr(target, 'setEnabled'):
                    target.setEnabled(True)

        animation.finished.connect(cleanup)


class HoverEventFilter(QtCore.QObject):
    """悬停事件过滤器"""

    def __init__(self, enter_callback: Callable, leave_callback: Callable):
        super().__init__()
        self.enter_callback = enter_callback
        self.leave_callback = leave_callback

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Enter:
            self.enter_callback()
        elif event.type() == QtCore.QEvent.Leave:
            self.leave_callback()

        return super().eventFilter(obj, event)


class ClickEventFilter(QtCore.QObject):
    """点击事件过滤器"""

    def __init__(self, click_callback: Callable):
        super().__init__()
        self.click_callback = click_callback

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self.click_callback(event.pos())

        return super().eventFilter(obj, event)


class LoadingIndicator(QtWidgets.QWidget):
    """加载指示器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.progress = -1  # -1 表示无限旋转

        self.setFixedSize(40, 40)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # 旋转定时器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._rotate)
        self.timer.setInterval(50)  # 20 FPS

        # 居中显示
        if parent:
            self.move(
                parent.width() // 2 - 20,
                parent.height() // 2 - 20
            )

    def start_spinning(self):
        """开始旋转动画"""
        self.progress = -1
        self.timer.start()

    def set_progress(self, progress: float):
        """设置进度（0-1）"""
        self.progress = max(0, min(1, progress))
        self.update()

    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.hide()

    def _rotate(self):
        """旋转更新"""
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        """绘制加载指示器"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        center = QtCore.QPointF(20, 20)
        radius = 15

        if self.progress < 0:
            # 无限旋转模式
            painter.translate(center)
            painter.rotate(self.angle)

            for i in range(8):
                alpha = 255 - (i * 30)
                color = QtGui.QColor(0, 255, 136, max(50, alpha))
                painter.setPen(QtGui.QPen(color, 3, QtCore.Qt.RoundCap))
                painter.drawLine(0, -radius, 0, -radius + 5)
                painter.rotate(45)
        else:
            # 进度模式
            painter.setPen(QtGui.QPen(QtGui.QColor('#4a4a4a'), 3))
            painter.drawEllipse(center, radius, radius)

            # 进度弧
            painter.setPen(QtGui.QPen(QtGui.QColor(
                '#00FF88'), 3, QtCore.Qt.RoundCap))
            start_angle = -90 * 16  # 从顶部开始
            span_angle = int(self.progress * 360 * 16)
            painter.drawArc(
                center.x() - radius, center.y() - radius,
                radius * 2, radius * 2,
                start_angle, span_angle
            )


class ClickParticle(QtWidgets.QWidget):
    """点击粒子效果"""

    def __init__(self, parent, center_pos):
        super().__init__(parent)
        self.center_pos = center_pos
        self.setFixedSize(20, 20)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # 随机方向和速度
        import random
        import math
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(20, 50)

        end_pos = QtCore.QPoint(
            center_pos.x() + int(math.cos(angle) * distance),
            center_pos.y() + int(math.sin(angle) * distance)
        )

        self.move(center_pos.x() - 10, center_pos.y() - 10)

        # 移动动画
        self.move_anim = QtCore.QPropertyAnimation(self, b"pos")
        self.move_anim.setDuration(500)
        self.move_anim.setStartValue(self.pos())
        self.move_anim.setEndValue(end_pos)
        self.move_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        # 淡出动画
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_anim = QtCore.QPropertyAnimation(
            self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)

        # 动画完成后删除
        self.fade_anim.finished.connect(self.deleteLater)

        # 开始动画
        self.move_anim.start()
        self.fade_anim.start()

    def paintEvent(self, event):
        """绘制粒子"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setBrush(QtGui.QColor('#00FF88'))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(5, 5, 10, 10)
