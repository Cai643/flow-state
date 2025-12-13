"""
精密动画引擎

提供高精度的动画效果，包括按钮动画、元素入场退场、数值滚动等。
"""

from PySide6 import QtCore, QtGui, QtWidgets
from enum import Enum
from typing import Optional, Callable


# 简化的AnimatedValue类（避免导入问题）
class AnimatedValue(QtCore.QObject):
    valueChanged = QtCore.Signal(float)

    def __init__(self, start_val=0.0):
        super().__init__()
        self._value = start_val
        self._anim = QtCore.QPropertyAnimation(self, b"value")

    @QtCore.Property(float)
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


class EasingType(Enum):
    """缓动函数类型"""
    EASE_IN_OUT_CUBIC = QtCore.QEasingCurve.InOutCubic
    EASE_OUT_BACK = QtCore.QEasingCurve.OutBack
    EASE_IN_OUT_ELASTIC = QtCore.QEasingCurve.InOutElastic
    EASE_OUT_BOUNCE = QtCore.QEasingCurve.OutBounce
    EASE_IN_OUT_QUAD = QtCore.QEasingCurve.InOutQuad
    EASE_OUT_QUAD = QtCore.QEasingCurve.OutQuad


class PrecisionAnimationEngine(QtCore.QObject):
    """精密动画引擎"""

    # 动画持续时间配置
    DURATION = {
        'fast': 150,
        'normal': 300,
        'slow': 500,
        'very_slow': 800
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_animations = []

    def create_button_press_animation(self, button: QtWidgets.QPushButton) -> QtCore.QPropertyAnimation:
        """创建按钮按下动画"""
        animation = QtCore.QPropertyAnimation(button, b"geometry")
        animation.setDuration(self.DURATION['fast'])
        animation.setEasingCurve(EasingType.EASE_OUT_BOUNCE.value)

        # 获取原始几何形状
        original_geo = button.geometry()

        # 按下时稍微缩小
        pressed_geo = QtCore.QRect(
            original_geo.x() + 2,
            original_geo.y() + 2,
            original_geo.width() - 4,
            original_geo.height() - 4
        )

        animation.setStartValue(original_geo)
        animation.setEndValue(pressed_geo)

        # 动画完成后恢复
        def restore_geometry():
            restore_anim = QtCore.QPropertyAnimation(button, b"geometry")
            restore_anim.setDuration(self.DURATION['fast'])
            restore_anim.setEasingCurve(EasingType.EASE_OUT_BACK.value)
            restore_anim.setStartValue(pressed_geo)
            restore_anim.setEndValue(original_geo)
            restore_anim.start()
            self._track_animation(restore_anim)

        animation.finished.connect(restore_geometry)
        self._track_animation(animation)
        return animation

    def create_fade_in_animation(self, widget: QtWidgets.QWidget, duration: int = None) -> QtCore.QPropertyAnimation:
        """创建淡入动画"""
        if duration is None:
            duration = self.DURATION['normal']

        # 创建透明度效果
        opacity_effect = QtWidgets.QGraphicsOpacityEffect()
        widget.setGraphicsEffect(opacity_effect)

        animation = QtCore.QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(EasingType.EASE_OUT_QUAD.value)

        self._track_animation(animation)
        return animation

    def create_fade_out_animation(self, widget: QtWidgets.QWidget, duration: int = None) -> QtCore.QPropertyAnimation:
        """创建淡出动画"""
        if duration is None:
            duration = self.DURATION['normal']

        # 获取现有的透明度效果或创建新的
        opacity_effect = widget.graphicsEffect()
        if not isinstance(opacity_effect, QtWidgets.QGraphicsOpacityEffect):
            opacity_effect = QtWidgets.QGraphicsOpacityEffect()
            widget.setGraphicsEffect(opacity_effect)

        animation = QtCore.QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(EasingType.EASE_IN_OUT_QUAD.value)

        self._track_animation(animation)
        return animation

    def create_scale_in_animation(self, widget: QtWidgets.QWidget, duration: int = None) -> QtCore.QPropertyAnimation:
        """创建缩放入场动画"""
        if duration is None:
            duration = self.DURATION['normal']

        # 保存原始几何形状
        original_geo = widget.geometry()
        center = original_geo.center()

        # 从中心点开始的小尺寸
        start_geo = QtCore.QRect(
            center.x() - 1, center.y() - 1, 2, 2
        )

        animation = QtCore.QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setStartValue(start_geo)
        animation.setEndValue(original_geo)
        animation.setEasingCurve(EasingType.EASE_OUT_BACK.value)

        self._track_animation(animation)
        return animation

    def create_scale_out_animation(self, widget: QtWidgets.QWidget, duration: int = None) -> QtCore.QPropertyAnimation:
        """创建缩放退场动画"""
        if duration is None:
            duration = self.DURATION['normal']

        original_geo = widget.geometry()
        center = original_geo.center()

        # 缩放到中心点
        end_geo = QtCore.QRect(
            center.x() - 1, center.y() - 1, 2, 2
        )

        animation = QtCore.QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setStartValue(original_geo)
        animation.setEndValue(end_geo)
        animation.setEasingCurve(EasingType.EASE_IN_OUT_CUBIC.value)

        self._track_animation(animation)
        return animation

    def create_number_roll_animation(self, start_val: float, end_val: float,
                                     duration: int = None) -> AnimatedValue:
        """创建数字滚动动画"""
        if duration is None:
            duration = self.DURATION['very_slow']

        animated_value = AnimatedValue(start_val)
        animated_value.animate_to(
            end_val, duration, 0, EasingType.EASE_OUT_QUAD.value)

        return animated_value

    def create_layout_resize_animation(self, widget: QtWidgets.QWidget,
                                       new_geometry: QtCore.QRect,
                                       duration: int = None) -> QtCore.QPropertyAnimation:
        """创建布局调整动画"""
        if duration is None:
            duration = self.DURATION['normal']

        animation = QtCore.QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setStartValue(widget.geometry())
        animation.setEndValue(new_geometry)
        animation.setEasingCurve(EasingType.EASE_IN_OUT_CUBIC.value)

        self._track_animation(animation)
        return animation

    def create_hover_animation(self, widget: QtWidgets.QWidget,
                               scale_factor: float = 1.05) -> QtCore.QPropertyAnimation:
        """创建悬停动画"""
        original_geo = widget.geometry()
        center = original_geo.center()

        # 计算放大后的几何形状
        new_width = int(original_geo.width() * scale_factor)
        new_height = int(original_geo.height() * scale_factor)

        hover_geo = QtCore.QRect(
            center.x() - new_width // 2,
            center.y() - new_height // 2,
            new_width,
            new_height
        )

        animation = QtCore.QPropertyAnimation(widget, b"geometry")
        animation.setDuration(self.DURATION['fast'])
        animation.setStartValue(original_geo)
        animation.setEndValue(hover_geo)
        animation.setEasingCurve(EasingType.EASE_OUT_QUAD.value)

        self._track_animation(animation)
        return animation

    def create_combined_entrance_animation(self, widget: QtWidgets.QWidget,
                                           duration: int = None) -> QtCore.QParallelAnimationGroup:
        """创建组合入场动画（淡入+缩放）"""
        if duration is None:
            duration = self.DURATION['normal']

        group = QtCore.QParallelAnimationGroup()

        # 淡入动画
        fade_anim = self.create_fade_in_animation(widget, duration)

        # 缩放动画
        scale_anim = self.create_scale_in_animation(widget, duration)

        group.addAnimation(fade_anim)
        group.addAnimation(scale_anim)

        self._track_animation(group)
        return group

    def create_combined_exit_animation(self, widget: QtWidgets.QWidget,
                                       duration: int = None) -> QtCore.QParallelAnimationGroup:
        """创建组合退场动画（淡出+缩放）"""
        if duration is None:
            duration = self.DURATION['normal']

        group = QtCore.QParallelAnimationGroup()

        # 淡出动画
        fade_anim = self.create_fade_out_animation(widget, duration)

        # 缩放动画
        scale_anim = self.create_scale_out_animation(widget, duration)

        group.addAnimation(fade_anim)
        group.addAnimation(scale_anim)

        self._track_animation(group)
        return group

    def _track_animation(self, animation):
        """跟踪动画以确保非阻塞性"""
        self._active_animations.append(animation)

        def cleanup():
            if animation in self._active_animations:
                self._active_animations.remove(animation)

        animation.finished.connect(cleanup)

    def stop_all_animations(self):
        """停止所有活动的动画"""
        for animation in self._active_animations[:]:
            animation.stop()
        self._active_animations.clear()

    @property
    def is_animating(self) -> bool:
        """检查是否有动画正在播放"""
        return len(self._active_animations) > 0
