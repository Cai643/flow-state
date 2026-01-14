"""
视觉效果管理器

提供现代化的视觉效果，包括阴影、渐变、发光等装饰效果。
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
from typing import List, Optional, Tuple


class VisualEffectsManager(QtCore.QObject):
    """视觉效果管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def apply_card_shadow(self, widget: QtWidgets.QWidget,
                          blur_radius: int = 15,
                          offset: Tuple[int, int] = (0, 4),
                          color: str = '#000000',
                          opacity: float = 0.3):
        """为卡片组件添加柔和阴影效果"""
        shadow_effect = QtWidgets.QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(blur_radius)
        shadow_effect.setOffset(offset[0], offset[1])
        shadow_effect.setColor(QtGui.QColor(color))

        # 设置透明度
        shadow_color = QtGui.QColor(color)
        shadow_color.setAlphaF(opacity)
        shadow_effect.setColor(shadow_color)

        widget.setGraphicsEffect(shadow_effect)

    def apply_button_gradient(self, button: QtWidgets.QPushButton,
                              colors: List[str] = None,
                              direction: str = 'vertical'):
        """为按钮应用渐变背景效果"""
        if colors is None:
            colors = ['#3a3a3a', '#2d2d2d']  # 默认暗色渐变

        if direction == 'vertical':
            gradient_style = f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {colors[0]}, stop:1 {colors[1]});
                    border: 1px solid #4a4a4a;
                    border-radius: 8px;
                    padding: 8px 16px;
                    color: #FFFFFF;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #00CC66, stop:1 #00FF88);
                    border-color: #00FF88;
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #00FF88, stop:1 #00CC66);
                }}
            """
        else:  # horizontal
            gradient_style = f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {colors[0]}, stop:1 {colors[1]});
                    border: 1px solid #4a4a4a;
                    border-radius: 8px;
                    padding: 8px 16px;
                    color: #FFFFFF;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #00CC66, stop:1 #00FF88);
                    border-color: #00FF88;
                }}
            """

        button.setStyleSheet(gradient_style)

    def apply_glow_border(self, widget: QtWidgets.QWidget,
                          color: str = '#00FF88',
                          intensity: float = 1.0):
        """应用发光边框效果"""
        # 创建自定义的发光效果
        class GlowEffect(QtWidgets.QGraphicsEffect):
            def __init__(self, color, intensity):
                super().__init__()
                self.glow_color = QtGui.QColor(color)
                self.intensity = intensity

            def draw(self, painter):
                # 绘制原始内容
                self.drawSource(painter)

                # 获取源图像
                source_pixmap = self.sourcePixmap()
                if source_pixmap.isNull():
                    return

                # 创建发光效果
                glow_pixmap = QtGui.QPixmap(source_pixmap.size())
                glow_pixmap.fill(QtCore.Qt.transparent)

                glow_painter = QtGui.QPainter(glow_pixmap)
                glow_painter.setCompositionMode(
                    QtGui.QPainter.CompositionMode_SourceOver)

                # 绘制多层发光
                for i in range(3):
                    blur_radius = (i + 1) * 2 * self.intensity
                    alpha = max(0.1, 0.5 - i * 0.15)

                    glow_color = QtGui.QColor(self.glow_color)
                    glow_color.setAlphaF(alpha)

                    # 这里简化处理，实际应用中可能需要更复杂的模糊算法
                    glow_painter.setPen(QtGui.QPen(glow_color, blur_radius))
                    glow_painter.setBrush(QtCore.Qt.NoBrush)
                    glow_painter.drawRect(source_pixmap.rect())

                glow_painter.end()

                # 绘制发光效果
                painter.drawPixmap(0, 0, glow_pixmap)

        # 应用发光效果
        glow_effect = GlowEffect(color, intensity)
        widget.setGraphicsEffect(glow_effect)

    def create_progress_bar_effect(self, progress_bar: QtWidgets.QProgressBar):
        """创建进度条的绿色渐变和动态光效"""
        progress_style = """
            QProgressBar {
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                background-color: #2d2d2d;
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00CC66, stop:0.5 #00FF88, stop:1 #00CC66);
                border-radius: 6px;
                margin: 1px;
            }
        """
        progress_bar.setStyleSheet(progress_style)

    def apply_separator_glow(self, separator: QtWidgets.QFrame):
        """为分隔线应用半透明发光效果"""
        separator_style = """
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 transparent, stop:0.5 rgba(0, 255, 136, 0.3), stop:1 transparent);
                border: none;
            }
        """
        separator.setStyleSheet(separator_style)

    def create_glass_effect(self, widget: QtWidgets.QWidget, opacity: float = 0.8):
        """创建毛玻璃效果"""
        # 创建半透明背景
        glass_style = f"""
            background-color: rgba(58, 58, 58, {int(opacity * 255)});
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
        """

        # 应用样式
        current_style = widget.styleSheet()
        widget.setStyleSheet(current_style + glass_style)

    def create_neon_text_effect(self, label: QtWidgets.QLabel,
                                color: str = '#00FF88',
                                glow_intensity: float = 1.0):
        """创建霓虹灯文字效果"""
        neon_style = f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                text-shadow: 
                    0 0 5px {color},
                    0 0 10px {color},
                    0 0 15px {color},
                    0 0 20px {color};
            }}
        """
        label.setStyleSheet(neon_style)

    def apply_hover_lift_effect(self, widget: QtWidgets.QWidget):
        """应用悬停上浮效果"""
        original_shadow = widget.graphicsEffect()

        def on_enter():
            # 增强阴影效果
            enhanced_shadow = QtWidgets.QGraphicsDropShadowEffect()
            enhanced_shadow.setBlurRadius(25)
            enhanced_shadow.setOffset(0, 8)
            enhanced_shadow.setColor(QtGui.QColor(0, 0, 0, 100))
            widget.setGraphicsEffect(enhanced_shadow)

        def on_leave():
            # 恢复原始阴影
            widget.setGraphicsEffect(original_shadow)

        # 连接事件（需要在实际使用时通过事件过滤器或子类化实现）
        return on_enter, on_leave

    def create_ripple_effect(self, widget: QtWidgets.QWidget,
                             click_pos: QtCore.QPoint,
                             color: str = '#00FF88'):
        """创建点击波纹效果"""
        # 这是一个简化的波纹效果实现
        # 实际应用中可能需要更复杂的动画和渲染

        class RippleWidget(QtWidgets.QWidget):
            def __init__(self, parent, center, color):
                super().__init__(parent)
                self.center = center
                self.color = QtGui.QColor(color)
                self.radius = 0
                self.max_radius = 100

                self.setGeometry(parent.rect())
                self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

                # 动画
                self.animation = QtCore.QPropertyAnimation(self, b"radius")
                self.animation.setDuration(500)
                self.animation.setStartValue(0)
                self.animation.setEndValue(self.max_radius)
                self.animation.setEasingCurve(QtCore.QEasingCurve.OutQuad)
                self.animation.finished.connect(self.deleteLater)
                self.animation.start()

            @QtCore.Property(int)
            def radius(self):
                return self._radius

            @radius.setter
            def radius(self, value):
                self._radius = value
                self.update()

            def paintEvent(self, event):
                painter = QtGui.QPainter(self)
                painter.setRenderHint(QtGui.QPainter.Antialiasing)

                # 计算透明度
                alpha = 1.0 - (self._radius / self.max_radius)
                color = QtGui.QColor(self.color)
                color.setAlphaF(alpha * 0.3)

                painter.setBrush(color)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(
                    self.center.x() - self._radius,
                    self.center.y() - self._radius,
                    self._radius * 2,
                    self._radius * 2
                )

        ripple = RippleWidget(widget, click_pos, color)
        ripple.show()
        return ripple
