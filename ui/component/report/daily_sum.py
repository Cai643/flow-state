import sys
import math
import random
from typing import List
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

try:
    from ui.component.visual_enhancements.starry_envelope import StarryEnvelopeWidget, ReportEnvelopeContainer
except ImportError:
    # 如果失败，可能是直接运行此文件，需要手动添加项目根目录到 path
    import sys
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    try:
        from ui.component.visual_enhancements.starry_envelope import StarryEnvelopeWidget, ReportEnvelopeContainer
    except ImportError:
        try:
            from ..visual_enhancements.starry_envelope import StarryEnvelopeWidget, ReportEnvelopeContainer
        except ImportError:
            # Fallback for direct execution if path setup worked
            from visual_enhancements.starry_envelope import StarryEnvelopeWidget, ReportEnvelopeContainer

# --- 统一主题配色 ---

try:
    from ui.component.report.report_theme import theme
except ImportError:
    try:
        from .report_theme import theme
    except ImportError:
        from report_theme import theme

# 向后兼容别名
MorandiTheme = theme

class DesignTokens:
    """统一的设计令牌系统 - 适配 ReportTheme"""

    # 颜色调色板 - 从 theme 获取
    COLORS = {
        'primary': theme.COLOR_TEXT_TITLE,        # Cream/Beige
        'primary_light': theme.COLOR_PRIMARY_LIGHT,  # Muted Teal
        'primary_dark': theme.COLOR_PRIMARY_DARK,   # Forest Green
        'secondary': theme.COLOR_TEXT_SECONDARY,      # Beige 80%
        'accent': theme.COLOR_ACCENT_DARK,         # Golden Yellow
        'accent_light': theme.COLOR_ACCENT_LIGHT,   # Pale Green
        'warning': theme.COLOR_WARNING,        # Orange
        'danger': theme.COLOR_DANGER,         # Red
        'text_primary': theme.COLOR_TEXT_TITLE,   # Beige/Cream
        'text_secondary': theme.COLOR_TEXT_SECONDARY, # Beige 80%
        'text_muted': theme.COLOR_TEXT_MUTED, # Pale Green 60%
        'background': theme.COLOR_BG_CENTER,     # Dark Deep Teal
        'surface': theme.COLOR_SURFACE,        # Forest Green
        'border': theme.COLOR_BORDER,          # Muted Teal
        'shadow': theme.COLOR_SHADOW,      # Shadow
        'overlay': theme.COLOR_OVERLAY  # Overlay
    }

    # 渐变色 - 使用 theme 颜色
    GRADIENTS = {
        'primary': [theme.COLOR_TEXT_TITLE, theme.COLOR_TEXT_TITLE],     # 金色
        'success': [theme.COLOR_TEXT_NORMAL, theme.COLOR_TEXT_NORMAL],     # 成功 (莫兰迪蓝)
        'accent': [theme.COLOR_TEXT_NORMAL, theme.COLOR_TEXT_NORMAL],      # 莫兰迪蓝渐变
        'warm': [theme.COLOR_DANGER, theme.COLOR_DANGER],        # 暖色
        'cool': [theme.COLOR_TEXT_NORMAL, theme.COLOR_TEXT_NORMAL],        # 冷色
        'dark': [theme.COLOR_BG_CENTER, theme.COLOR_BG_EDGE] # 星空渐变
    }

    # 阴影系统
    SHADOWS = {
        'sm': {'blur': 4, 'offset': (0, 2), 'color': 'rgba(0, 0, 0, 0.1)'},
        'md': {'blur': 8, 'offset': (0, 4), 'color': 'rgba(0, 0, 0, 0.12)'},
        'lg': {'blur': 16, 'offset': (0, 8), 'color': 'rgba(0, 0, 0, 0.15)'},
        'xl': {'blur': 24, 'offset': (0, 12), 'color': 'rgba(0, 0, 0, 0.18)'}
    }

    # 动画缓动
    EASINGS = {
        'ease_out': QtCore.QEasingCurve.OutCubic,
        'ease_in': QtCore.QEasingCurve.InCubic,
        'ease_in_out': QtCore.QEasingCurve.InOutCubic,
        'bounce': QtCore.QEasingCurve.OutBounce,
        'elastic': QtCore.QEasingCurve.OutElastic,
        'back': QtCore.QEasingCurve.OutBack
    }

# --- 数据模型 ---


class InterfaceState:
    """界面状态模型"""

    def __init__(self):
        self.is_collapsed = True
        self.animation_in_progress = False
        self.current_height = 280  # 折叠模式高度 (仅显示信封)
        self.expanded_height = 950  # 展开模式高度


class TimelineEntry:
    """时间轴条目数据结构"""

    def __init__(self, start_time: str, end_time: str, activity_type: str, description: str, color: str):
        self.start_time = start_time
        self.end_time = end_time
        self.activity_type = activity_type  # 'work', 'rest', 'break'
        self.description = description
        self.color = color


class AnimationConfig:
    """动画配置模型"""
    collapse_duration = 400
    expand_duration = 500
    particle_duration = 2000
    easing_curve = DesignTokens.EASINGS['ease_in_out']

# --- 增强的动画系统 ---


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


class ParticleEffect(QtCore.QObject):
    """增强的粒子效果系统"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.particles = []
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.is_active = False

    def create_celebration_particles(self, center_point, count=15):
        """创建庆祝粒子效果"""
        print(f"创建 {count} 个粒子在位置 {center_point}")  # 调试信息
        self.particles.clear()

        # 创建多种类型的粒子
        for i in range(count):
            angle = (360 / count) * i + (random.random() * 30 - 15)  # 添加随机偏移
            speed = 2 + random.random() * 3  # 随机速度

            particle = {
                'x': float(center_point.x()),
                'y': float(center_point.y()),
                'vx': math.cos(math.radians(angle)) * speed,
                'vy': math.sin(math.radians(angle)) * speed,
                'life': 1.0,
                'max_life': 1.0,
                'size': 3 + random.random() * 4,  # 随机大小
                'color': self._get_random_color(),
                'rotation': 0,
                'rotation_speed': (random.random() - 0.5) * 10
            }
            self.particles.append(particle)

        print(f"创建了 {len(self.particles)} 个粒子")  # 调试信息

        if not self.is_active:
            self.is_active = True
            self.timer.start(16)  # 60fps
            print("启动粒子动画定时器")  # 调试信息

    def _get_random_color(self):
        """获取随机的庆祝颜色"""
        colors = [
            DesignTokens.COLORS['accent'],
            DesignTokens.COLORS['primary'],
            DesignTokens.COLORS['secondary'],
            theme.COLOR_DANGER.name(),     # 红色
            theme.COLOR_PRIMARY_LIGHT.name(), # 青色/浅绿
            theme.COLOR_BORDER.name(),     # 蓝色/灰蓝
            theme.COLOR_WARNING.name(),    # 黄色
        ]
        return colors[int(random.random() * len(colors))]

    def update_particles(self):
        """优化的粒子状态更新"""
        if not self.particles:
            self.timer.stop()
            self.is_active = False
            return

        # 使用列表推导式批量处理，提高性能
        updated_particles = []

        for particle in self.particles:
            # 更新位置
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']

            # 物理效果
            particle['vy'] += 0.12  # 重力（稍微减少以获得更好的视觉效果）
            particle['vx'] *= 0.985  # 空气阻力
            particle['vy'] *= 0.985

            # 更新生命值（根据粒子大小调整衰减速度）- 减慢衰减让粒子更持久
            life_decay = 0.008 + (particle['size'] - 3) * 0.001  # 减少衰减速度
            particle['life'] -= life_decay

            # 更新旋转
            particle['rotation'] += particle['rotation_speed']

            # 添加轻微的随机扰动以增加自然感
            if random.random() < 0.1:
                particle['vx'] += (random.random() - 0.5) * 0.2
                particle['vy'] += (random.random() - 0.5) * 0.2

            # 只保留活着的粒子
            if particle['life'] > 0:
                updated_particles.append(particle)

        # 批量更新粒子列表
        self.particles = updated_particles

        # 优化：只在有粒子时触发重绘
        if self.particles and self.parent:
            # 如果父窗口有粒子覆盖层，优先更新覆盖层
            if hasattr(self.parent, 'particle_overlay'):
                self.parent.particle_overlay.update()
            else:
                self.parent.update()
        elif not self.particles:
            # 所有粒子都消失了，停止定时器
            self.timer.stop()
            self.is_active = False

    def draw_particles(self, painter):
        """绘制优化的粒子效果"""
        if not self.particles:
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # 批量处理粒子以提高性能
        alive_particles = [p for p in self.particles if p['life'] > 0]

        if not alive_particles:
            painter.restore()
            return

        # 按生命值排序，先绘制生命值低的（更透明的）
        alive_particles.sort(key=lambda p: p['life'])

        for particle in alive_particles:
            # 计算透明度和缩放
            alpha_factor = particle['life'] / particle['max_life']

            # 添加脉冲效果
            pulse_factor = 1.0 + 0.3 * math.sin(particle['rotation'] * 0.1)
            current_size = particle['size'] * pulse_factor

            # 计算位置
            x, y = int(particle['x']), int(particle['y'])

            # 优化：只在粒子可见时绘制
            if alpha_factor < 0.01:
                continue

            # 创建渐变画刷以获得更好的视觉效果
            gradient = QtGui.QRadialGradient(x, y, current_size / 2)

            # 核心颜色
            core_color = QtGui.QColor(particle['color'])
            core_color.setAlpha(int(255 * alpha_factor))

            # 边缘颜色（更透明）
            edge_color = QtGui.QColor(particle['color'])
            edge_color.setAlpha(int(100 * alpha_factor))

            gradient.setColorAt(0, core_color)
            gradient.setColorAt(0.7, edge_color)
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))  # 完全透明

            # 绘制发光效果（外层）
            if alpha_factor > 0.3:  # 只在粒子足够不透明时绘制发光
                glow_size = current_size * 1.8
                glow_gradient = QtGui.QRadialGradient(x, y, glow_size / 2)

                glow_color = QtGui.QColor(particle['color'])
                glow_color.setAlpha(int(60 * alpha_factor))

                glow_gradient.setColorAt(0, glow_color)
                glow_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))

                painter.setBrush(glow_gradient)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(
                    int(x - glow_size / 2), int(y - glow_size / 2),
                    int(glow_size), int(glow_size)
                )

            # 绘制主粒子
            painter.setBrush(gradient)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(
                int(x - current_size / 2), int(y - current_size / 2),
                int(current_size), int(current_size)
            )

            # 添加闪烁效果（随机亮点）
            if random.random() < 0.1 * alpha_factor:  # 10%概率闪烁
                sparkle_size = current_size * 0.3
                sparkle_color = QtGui.QColor(
                    255, 255, 255, int(200 * alpha_factor))
                painter.setBrush(sparkle_color)
                painter.drawEllipse(
                    int(x - sparkle_size / 2), int(y - sparkle_size / 2),
                    int(sparkle_size), int(sparkle_size)
                )

        painter.restore()

    def stop(self):
        """停止粒子效果"""
        self.particles.clear()
        if self.timer.isActive():
            self.timer.stop()
        self.is_active = False

# --- 增强功能组件 ---


class _StarryEnvelopeWidget_Deprecated(QtWidgets.QWidget):
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
        self.border_color = QtGui.QColor(DesignTokens.COLORS['border'])
        self.border_color.setAlpha(self.border_alpha)
        
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
        
        # 1. 背景渐变 (更新为带透明度的蓝->紫，饱和度降低)
        gradient = QtGui.QLinearGradient(0, 0, 0, 180) # 从上到下
        
        bg_color = QtGui.QColor(DesignTokens.COLORS['background'])
        bg_color.setAlpha(230)
        
        surface_color = QtGui.QColor(DesignTokens.COLORS['surface'])
        surface_color.setAlpha(230)
        
        # 起始
        gradient.setColorAt(0, bg_color)
        # 结束
        gradient.setColorAt(1, surface_color)
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
                
            pen = QtGui.QPen(QtGui.QColor(DesignTokens.COLORS['accent_light']), 1)
            painter.setPen(pen)
            
            sx = self.shooting_star['start_x'] + (self.shooting_star['end_x'] - self.shooting_star['start_x']) * p
            sy = self.shooting_star['start_y'] + (self.shooting_star['end_y'] - self.shooting_star['start_y']) * p
            # 绘制轨迹
            painter.drawLine(QtCore.QPointF(sx, sy), QtCore.QPointF(sx-3, sy-3))

        # 4. 文本
        # 主标题 (位置针对新尺寸调整)
        painter.setPen(QtGui.QColor(DesignTokens.COLORS['primary']))
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
        
        painter.drawText(rect.adjusted(0, 45, 0, 0), QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, "一封来自星星的信")
        
        # 副标题 (位置针对新尺寸调整)
        c_sub = QtGui.QColor(DesignTokens.COLORS['accent_light'])
        c_sub.setAlpha(204)
        painter.setPen(c_sub)
        font_sub = QtGui.QFont("Noto Sans SC")
        font_sub.setPixelSize(12)
        painter.setFont(font_sub)
        painter.drawText(rect.adjusted(0, 75, 0, 0), QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter, "点开就进入下一个界面")
        
        # 5. Emoji 装饰 (位置针对新尺寸调整)
        painter.setPen(QtGui.QColor(DesignTokens.COLORS['primary']))
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
            self.border_color = QtGui.QColor(DesignTokens.COLORS['border'])
            self.border_width = 4.0
            self.shadow.setBlurRadius(8)
            self.shadow.setOffset(0, 2)
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.disappearing:
            self.disappearing = True
            # 开始消失动画
            self.disappear_timer = QtCore.QTimer(self)
            self.disappear_progress = 0.0
            self.disappear_timer.timeout.connect(self.update_disappear)
            self.disappear_timer.start(16)

    def update_disappear(self):
        self.disappear_progress += 0.05
        if self.disappear_progress >= 1.0:
            self.disappear_timer.stop()
            self.clicked.emit()
            self.hide()
        else:
            self.scale_factor = 0.98 * (1.0 - 0.2 * self.disappear_progress)
            self.opacity = 1.0 - self.disappear_progress
            self.rotation = 5.0 * self.disappear_progress
            self.update()


class CollapsibleContainer(QtWidgets.QWidget):
    """可折叠的容器组件"""

    stateChanged = Signal(bool)  # 状态改变信号，True为展开，False为折叠

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = InterfaceState()
        self.compact_widget = None
        self.expanded_widget = None

        # 创建主布局
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 创建内容容器
        self.content_container = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.toggle_button = StarryEnvelopeWidget()
        self.toggle_button.set_gradient("#D4E0BB", "#E0E1AC")
        self.toggle_button.clicked.connect(self.toggle_state)
        
        # 居中容器
        self.envelope_container = QtWidgets.QWidget()
        self.envelope_layout = QtWidgets.QHBoxLayout(self.envelope_container)
        self.envelope_layout.setContentsMargins(0, 10, 0, 10)
        self.envelope_layout.addStretch()
        self.envelope_layout.addWidget(self.toggle_button)
        self.envelope_layout.addStretch()

        # 添加到主布局
        self.main_layout.addWidget(self.envelope_container)
        self.main_layout.addWidget(self.content_container)

        # 动画系统
        self.height_anim = AnimatedValue(self.state.current_height)
        self.height_anim.valueChanged.connect(self._update_height)

        # 内容透明度动画
        self.content_opacity = AnimatedValue(1.0)
        self.content_opacity.valueChanged.connect(self._update_content_opacity)

        # 设置初始状态
        self.setFixedHeight(self.state.current_height)
        self._update_content_visibility()

    def set_collapsed(self, collapsed: bool):
        """设置折叠状态"""
        if self.state.is_collapsed == collapsed or self.state.animation_in_progress:
            return

        self.state.is_collapsed = collapsed
        self.state.animation_in_progress = True

        # 先淡出当前内容
        self.content_opacity.animate_to(
            0.0, 150, 0, DesignTokens.EASINGS['ease_out'])

        # 延迟切换内容和调整高度
        QtCore.QTimer.singleShot(150, self._switch_content_and_animate)

        self.stateChanged.emit(not collapsed)  # True为展开

    def _switch_content_and_animate(self):
        """切换内容并执行高度动画"""
        # 更新内容显示
        self._update_content_visibility()
        self._update_toggle_button()

        # 计算目标高度
        target_height = self.state.current_height if self.state.is_collapsed else self.state.expanded_height
        duration = AnimationConfig.collapse_duration if self.state.is_collapsed else AnimationConfig.expand_duration

        # 执行高度动画
        self.height_anim.animate_to(
            target_height, duration, 0, AnimationConfig.easing_curve)

        # 淡入新内容
        QtCore.QTimer.singleShot(duration // 2, lambda: self.content_opacity.animate_to(
            1.0, 200, 0, DesignTokens.EASINGS['ease_in']))

    def is_collapsed(self) -> bool:
        """返回当前是否为折叠状态"""
        return self.state.is_collapsed

    def toggle_state(self):
        """切换折叠/展开状态"""
        old_state = self.state.is_collapsed
        self.set_collapsed(not self.state.is_collapsed)

        # 如果是从折叠变为展开，触发额外的粒子效果
        if old_state and not self.state.is_collapsed:
            print("检测到展开操作，准备触发粒子效果")  # 调试信息

    def set_compact_content(self, widget: QtWidgets.QWidget):
        """设置折叠模式的内容"""
        if self.compact_widget:
            self.content_layout.removeWidget(self.compact_widget)
            self.compact_widget.setParent(None)

        self.compact_widget = widget
        if widget:
            self.content_layout.addWidget(widget)
            if not self.state.is_collapsed:
                widget.hide()

    def set_expanded_content(self, widget: QtWidgets.QWidget):
        """设置展开模式的内容"""
        if self.expanded_widget:
            self.content_layout.removeWidget(self.expanded_widget)
            self.expanded_widget.setParent(None)

        self.expanded_widget = widget
        if widget:
            self.content_layout.addWidget(widget)
            if self.state.is_collapsed:
                widget.hide()

    def _update_content_visibility(self):
        """更新内容可见性"""
        if self.state.is_collapsed:
            if self.expanded_widget:
                self.expanded_widget.hide()
            if self.compact_widget:
                self.compact_widget.show()
            
            # Show envelope
            if hasattr(self, 'envelope_container'):
                self.envelope_container.show()
                # Reset envelope state
                self.toggle_button.show()
                self.toggle_button.opacity = 1.0
                self.toggle_button.scale_factor = 1.0
                self.toggle_button.disappearing = False
                self.toggle_button.update()
        else:
            if self.compact_widget:
                self.compact_widget.hide()
            if self.expanded_widget:
                self.expanded_widget.show()
            
            # Hide envelope
            if hasattr(self, 'envelope_container'):
                self.envelope_container.hide()

    def _update_toggle_button(self):
        """更新切换按钮的样式和文字"""
        # 星空信封不需要更新文字和样式
        pass

    def _update_height(self, height: float):
        """更新容器高度"""
        self.setFixedHeight(int(height))
        if abs(height - self.height_anim._anim.endValue()) < 1:
            self.state.animation_in_progress = False

    def _update_content_opacity(self, opacity: float):
        """更新内容透明度"""
        effect = QtWidgets.QGraphicsOpacityEffect()
        effect.setOpacity(opacity)
        self.content_container.setGraphicsEffect(effect)


class ImageExporter(QtCore.QObject):
    """图片导出功能组件"""

    exportStarted = Signal()
    exportCompleted = Signal(str)  # 导出完成，参数为文件路径
    exportFailed = Signal(str)     # 导出失败，参数为错误信息

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self.parent_widget = parent_widget

    def export_to_file(self) -> bool:
        """导出界面为图片文件"""
        try:
            self.exportStarted.emit()

            # 显示文件选择对话框
            file_path = self._show_file_dialog()
            if not file_path:
                return False

            # 验证文件路径
            if not self._validate_file_path(file_path):
                return False

            # 渲染界面为图片
            pixmap = self._render_widget_to_pixmap()
            if pixmap.isNull():
                self.exportFailed.emit("无法渲染界面内容")
                return False

            # 确定图片格式
            file_format = "PNG"
            if file_path.lower().endswith(('.jpg', '.jpeg')):
                file_format = "JPEG"

            # 保存图片
            if pixmap.save(file_path, file_format):
                self.exportCompleted.emit(file_path)
                return True
            else:
                self.exportFailed.emit(f"保存图片文件失败: {file_path}")
                return False

        except Exception as e:
            self.exportFailed.emit(f"导出过程中发生错误: {str(e)}")
            return False

    def _render_widget_to_pixmap(self) -> QtGui.QPixmap:
        """将界面渲染为QPixmap"""
        size = self.parent_widget.size()
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        self.parent_widget.render(painter)
        painter.end()

        return pixmap

    def _show_file_dialog(self) -> str:
        """显示文件保存对话框"""
        import os
        from datetime import datetime

        # 生成默认文件名（包含日期时间）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"daily_report_{timestamp}.png"

        # 获取用户文档目录作为默认保存位置
        documents_path = os.path.expanduser("~/Documents")
        default_path = os.path.join(documents_path, default_filename)

        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        file_dialog.setNameFilter("PNG图片 (*.png);;JPEG图片 (*.jpg);;所有文件 (*)")
        file_dialog.setDefaultSuffix("png")

        file_path, selected_filter = file_dialog.getSaveFileName(
            self.parent_widget,
            "保存日报图片",
            default_path,
            "PNG图片 (*.png);;JPEG图片 (*.jpg);;所有文件 (*)"
        )

        return file_path

    def _validate_file_path(self, file_path: str) -> bool:
        """验证文件路径是否有效"""
        import os

        if not file_path:
            return False

        # 检查目录是否存在且可写
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError:
                self.exportFailed.emit(f"无法创建目录: {directory}")
                return False

        if not os.access(directory, os.W_OK):
            self.exportFailed.emit(f"没有写入权限: {directory}")
            return False

        return True


class FeedbackSystem(QtCore.QObject):
    """用户反馈系统"""

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self.parent_widget = parent_widget

    def show_success_message(self, message: str, file_path: str = None):
        """显示成功消息"""
        # 创建成功提示对话框
        msg_box = QtWidgets.QMessageBox(self.parent_widget)
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setWindowTitle("导出成功")
        msg_box.setText(message)

        if file_path:
            msg_box.setDetailedText(f"文件已保存到: {file_path}")

            # 添加打开文件夹按钮
            open_folder_btn = msg_box.addButton(
                "打开文件夹", QtWidgets.QMessageBox.ActionRole)
            open_folder_btn.clicked.connect(
                lambda: self._open_file_location(file_path))

        msg_box.addButton("确定", QtWidgets.QMessageBox.AcceptRole)

        # 设置样式
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {DesignTokens.COLORS['background']};
                color: {DesignTokens.COLORS['text_primary']};
            }}
            QMessageBox QPushButton {{
                background-color: {DesignTokens.COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {DesignTokens.COLORS['primary_dark']};
            }}
        """)

        msg_box.exec_()

    def show_error_message(self, error_message: str):
        """显示错误消息"""
        msg_box = QtWidgets.QMessageBox(self.parent_widget)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle("导出失败")
        msg_box.setText("图片导出过程中发生错误")
        msg_box.setDetailedText(error_message)
        msg_box.addButton("确定", QtWidgets.QMessageBox.AcceptRole)

        # 设置样式
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {DesignTokens.COLORS['background']};
                color: {DesignTokens.COLORS['text_primary']};
            }}
            QMessageBox QPushButton {{
                background-color: {DesignTokens.COLORS['danger']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 500;
            }}
            QMessageBox QPushButton:hover {{
                background-color: #c0392b;
            }}
        """)

        msg_box.exec_()

    def show_particle_celebration(self, center_point: QtCore.QPoint):
        """显示粒子庆祝效果"""
        # 这个方法将在主界面中调用粒子效果
        if hasattr(self.parent_widget, 'particle_effect'):
            self.parent_widget.particle_effect.create_celebration_burst(
                center_point, 15)

    def _open_file_location(self, file_path: str):
        """打开文件所在位置"""
        import os
        import subprocess
        import platform

        try:
            directory = os.path.dirname(file_path)

            system = platform.system()
            if system == "Windows":
                os.startfile(directory)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", directory])
            else:  # Linux
                subprocess.run(["xdg-open", directory])
        except Exception as e:
            print(f"无法打开文件夹: {e}")


class TimelineView(QtWidgets.QWidget):
    """精美的时间轴视图组件"""
    
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline_entries = []
        self.setWindowTitle("📊 今日时间轴 - 专注历程")
        self.setFixedSize(1000, 700)  # 保持原尺寸
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 设置窗口样式
        # self.setStyleSheet(...) # 移除旧样式，完全依靠 paintEvent

        # 创建示例数据
        self._create_sample_data()

        # 动画系统
        self.fade_anim = AnimatedValue(0.0)
        self.fade_anim.valueChanged.connect(self.update)

        # 时间段动画
        self.segment_animations = []
        for i in range(len(self.timeline_entries)):
            anim = AnimatedValue(0.0)
            anim.valueChanged.connect(self.update)
            self.segment_animations.append(anim)
            
        # 初始化星星
        self.stars = self._init_stars()
        self.star_timer = QtCore.QTimer(self)
        self.star_timer.timeout.connect(self.update_stars)
        
        # 背景粒子效果
        self.background_particles = []
        self.particle_timer = QtCore.QTimer(self)
        self.particle_timer.timeout.connect(self._update_background_particles)

        # 悬停效果
        self.hover_segment = -1
        self.setMouseTracking(True)

        # 统计数据动画
        self.stats_anim = AnimatedValue(0.0)
        self.stats_anim.valueChanged.connect(self.update)

        # 创建粒子覆盖层用于入场效果
        self.particle_overlay = ParticleOverlay(self)

    def changeEvent(self, event):
        """处理窗口状态变化"""
        if event.type() == QtCore.QEvent.ActivationChange:
            # 如果失去焦点，关闭窗口
            if not self.isActiveWindow():
                self.close()
        super().changeEvent(event)

    def hideEvent(self, event):
        """隐藏事件（包括关闭）"""
        self.closed.emit()
        super().hideEvent(event)

    def closeEvent(self, event):
        """关闭事件"""
        # closeEvent 也会导致 hide，所以信号可能发两次，但这没关系，只要能发出去就行
        self.closed.emit()
        super().closeEvent(event)

    def set_timeline_data(self, entries):
        """设置时间轴数据"""
        self.timeline_entries = entries
        self.update()

    def show_timeline(self):
        """显示时间轴窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

        # 启动淡入动画
        self.fade_anim.animate_to(
            1.0, 800, 0, DesignTokens.EASINGS['ease_out'])

        # 启动错开的时间段动画
        self._start_segment_animations()

        # 启动统计数据动画
        self.stats_anim.animate_to(
            1.0, 1000, 600, DesignTokens.EASINGS['back'])

        # 启动背景粒子效果
        self._create_background_particles()
        self.particle_timer.start(50)  # 20fps
        self.star_timer.start(50) # 启动星星动画

        # 添加入场金色粒子效果
        self._create_entrance_particles()

        # 设置并显示粒子覆盖层
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.show()
            self.particle_overlay.raise_()

    def _init_stars(self):
        stars = []
        # 3颗主星 (80%透明)
        for _ in range(3):
            stars.append({
                'type': 'main',
                'x': random.randint(20, 980),
                'y': random.randint(20, 680),
                'size': 3,
                'delay': random.random() * 2,
                'alpha': 204
            })
        # 5颗背景星 (15%透明)
        for _ in range(5):
            stars.append({
                'type': 'bg',
                'x': random.randint(20, 980),
                'y': random.randint(20, 680),
                'size': 2,
                'delay': random.random() * 5,
                'alpha': 38
            })
        return stars

    def update_stars(self):
        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0
        for star in self.stars:
            if star['type'] == 'main':
                # 2秒周期
                t = (current_time + star['delay']) % 2.0
                norm = t / 1.0 if t < 1.0 else (2.0 - t) / 1.0
                star['alpha'] = 204 + (51 * norm)
            else:
                # 8秒周期
                t = (current_time + star['delay']) % 8.0
                norm = t / 4.0 if t < 4.0 else (8.0 - t) / 4.0
                star['alpha'] = 20 + (30 * norm)
        self.update()

    def _create_sample_data(self):
        """创建示例时间轴数据"""
        self.timeline_entries = [
            TimelineEntry("09:30", "11:02", "work",
                          "完成了主要代码的编写，专注度拉满！💻", DesignTokens.COLORS['primary']),
            TimelineEntry("11:02", "11:15", "break", "短暂休息，喝杯咖啡☕",
                          DesignTokens.COLORS['accent']),
            TimelineEntry("11:15", "13:00", "work", "继续编码，解决了几个难题🔧",
                          DesignTokens.COLORS['primary']),
            TimelineEntry("13:00", "14:00", "rest", "午餐时间，补充能量🍽️",
                          DesignTokens.COLORS['secondary']),
            TimelineEntry("14:00", "16:30", "work", "专心工作，完成重要功能✨",
                          DesignTokens.COLORS['primary']),
            TimelineEntry("16:30", "16:45", "break", "眼部休息，远眺放松👀",
                          DesignTokens.COLORS['accent']),
            TimelineEntry("16:45", "18:00", "work", "代码审查和文档整理📝",
                          DesignTokens.COLORS['primary'])
        ]

    def _start_segment_animations(self):
        """启动错开的时间段动画"""
        for i, anim in enumerate(self.segment_animations):
            delay = 400 + i * 150  # 每个时间段延迟150ms
            anim.animate_to(1.0, 800, delay, DesignTokens.EASINGS['back'])

    def _create_background_particles(self):
        """创建背景装饰粒子"""
        self.background_particles.clear()
        for i in range(15):
            particle = {
                'x': random.random() * self.width(),
                'y': random.random() * self.height(),
                'vx': (random.random() - 0.5) * 0.5,
                'vy': (random.random() - 0.5) * 0.5,
                'size': 1 + random.random() * 3,
                'alpha': 0.1 + random.random() * 0.2,
                'color': random.choice([
                    DesignTokens.COLORS['primary'],
                    DesignTokens.COLORS['secondary'],
                    DesignTokens.COLORS['accent']
                ])
            }
            self.background_particles.append(particle)

    def _create_entrance_particles(self):
        """创建时间轴入场金色粒子效果"""
        # 创建专门的粒子效果对象
        self.entrance_particle_effect = EnhancedParticleEffect(self)

        # 使用增强粒子效果创建时间轴入场效果
        self.entrance_particle_effect.create_timeline_entrance_effect()

        # 设置到粒子覆盖层
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.set_particle_effect(
                self.entrance_particle_effect)
            self.particle_overlay.update_geometry()

    def _get_golden_colors(self):
        """获取金色系粒子颜色"""
        return [
            '#FFD700',  # 金色
            '#FFA500',  # 橙色
            '#FFFF00',  # 黄色
            '#FFE55C',  # 浅金色
            '#FFC125',  # 深金色
            '#DAA520',  # 暗金色
            '#F0E68C',  # 卡其色
            '#FFEB3B',  # 亮黄色
            '#FFF176',  # 浅黄色
        ]

    def _update_background_particles(self):
        """更新背景粒子"""
        for particle in self.background_particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']

            # 边界反弹
            if particle['x'] <= 0 or particle['x'] >= self.width():
                particle['vx'] *= -1
            if particle['y'] <= 0 or particle['y'] >= self.height():
                particle['vy'] *= -1

            # 保持在边界内
            particle['x'] = max(0, min(self.width(), particle['x']))
            particle['y'] = max(0, min(self.height(), particle['y']))

        self.update()

    def paintEvent(self, event):
        """绘制精美的时间轴"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        # 应用淡入效果（如果动画未生效则默认不透明，避免内容看不见）
        fade_opacity = self.fade_anim.value
        if fade_opacity <= 0:
            fade_opacity = 1.0
        painter.setOpacity(fade_opacity)

        # 绘制背景粒子
        self._draw_background_particles(painter)
        
        # 绘制星星
        for star in self.stars:
            c = QtGui.QColor("#F9A825") # 金色星星
            c.setAlpha(int(star['alpha']))
            painter.setBrush(c)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(star['x'], star['y']), star['size'], star['size'])

        # 绘制主要内容（入场粒子效果现在由覆盖层处理）
        self._draw_timeline(painter)

    def _draw_background_particles(self, painter: QtGui.QPainter):
        """绘制背景装饰粒子"""
        painter.save()
        for particle in self.background_particles:
            color = QtGui.QColor(particle['color'])
            color.setAlphaF(particle['alpha'])
            painter.setBrush(color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(
                int(particle['x'] - particle['size']/2),
                int(particle['y'] - particle['size']/2),
                int(particle['size']),
                int(particle['size'])
            )
        painter.restore()

    def _draw_timeline(self, painter: QtGui.QPainter):
        """绘制精美的时间轴内容"""
        rect = self.rect()
        margin = 80
        header_height = 160  # 进一步增加标题区域高度
        footer_height = 140  # 增加底部区域高度
        timeline_y = header_height + 180  # 调整时间轴位置，给文本更多空间
        timeline_width = rect.width() - 2 * margin

        # 绘制渐变背景
        # 径向渐变背景 (莫兰迪蓝星空 - 8%透明)
        bg_gradient = QtGui.QRadialGradient(rect.center(), max(rect.width(), rect.height()) / 1.2)
        
        # 使用 MorandiTheme 定义的颜色
        # bg_gradient.setColorAt(0, MorandiTheme.COLOR_BG_CENTER)
        # bg_gradient.setColorAt(1, MorandiTheme.COLOR_BG_EDGE)
        
        # 自定义深色背景板，增强对比度 (在这里修改背景颜色和透明度)
        # 中心：主题中心色
        c_center = DesignTokens.COLORS['background']
        # 边缘：主题边缘色 (或者 surface)
        c_edge = DesignTokens.COLORS['surface']
        
        bg_gradient.setColorAt(0, c_center)
        bg_gradient.setColorAt(1, c_edge)
        
        painter.setBrush(bg_gradient)
        painter.setPen(QtCore.Qt.NoPen)
        
        # 绘制容器形状：顶部0px，底部12px圆角
        path = QtGui.QPainterPath()
        path.moveTo(rect.left(), rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom() - 12)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - 12, rect.bottom())
        path.lineTo(rect.left() + 12, rect.bottom())
        path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - 12)
        path.closeSubpath()
        
        painter.drawPath(path)
        
        # 边框 (仅保留 左、右、下)
        border_pen = QtGui.QPen(MorandiTheme.COLOR_BORDER, 2)
        painter.setPen(border_pen)
        # 移除 drawPolyline，使用下方的 path_border 绘制平滑圆角边框
        
        # 补圆角线段 (绘制三边 + 两个圆角)
        # 简单处理：重新绘制 path 但只描边
        painter.setBrush(QtCore.Qt.NoBrush)
        # 由于drawPath会画上边框，我们需要屏蔽上边框。
        # 这里为了简单，直接画一个遮盖或者只画三边。
        # 实际上，drawPath 已经很好了，上边框如果是 30% 透明也无所谓，但用户说 "顶部无边框"。
        # 我们可以单独画三条线 + 两个圆角。
        # 简单方案：Path 不闭合
        path_border = QtGui.QPainterPath()
        path_border.moveTo(rect.left(), rect.top())
        path_border.lineTo(rect.left(), rect.bottom() - 12)
        path_border.quadTo(rect.left(), rect.bottom(), rect.left() + 12, rect.bottom())
        path_border.lineTo(rect.right() - 12, rect.bottom())
        path_border.quadTo(rect.right(), rect.bottom(), rect.right(), rect.bottom() - 12)
        path_border.lineTo(rect.right(), rect.top())
        painter.drawPath(path_border)
        
        # 内阴影 (inset 0 0 20px)
        # 简单模拟
        
        # 绘制精美标题区域 (不再绘制，直接留空)
        # self._draw_header(painter, margin, header_height)

        # 绘制主时间轴线（带渐变效果）
        self._draw_main_timeline(painter, margin, timeline_y, timeline_width)

        # 绘制时间刻度 (Moved after main timeline to ensure visibility if needed, or keep before)
        # Actually, let's redraw time scale using Morandi colors
        self._draw_time_scale(painter, margin, timeline_y - 40, timeline_width)

        # 绘制时间段（带动画和悬停效果）
        for i, entry in enumerate(self.timeline_entries):
            if i < len(self.segment_animations):
                animation_progress = self.segment_animations[i].value
                # 如果动画系统未生效，保证时间轴内容始终可见
                if animation_progress <= 0:
                    animation_progress = 1.0
                is_hovered = (i == self.hover_segment)
                self._draw_timeline_entry(
                    painter, entry, i, margin, timeline_y, timeline_width,
                    animation_progress, is_hovered)

        # 绘制统计信息 - 进一步增加间距，避免与时间段文本重叠
        # 背景：主题背景
        # 边框：主题边框
        
        stats_rect = QtCore.QRectF(margin, timeline_y + 220, timeline_width, 120)
        
        # 背景
        bg_color = QtGui.QColor(DesignTokens.COLORS['background'])
        bg_color.setAlpha(200) # Slightly transparent
        painter.setBrush(bg_color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(stats_rect, 12, 12)
        
        # 边框 (顶部1px) - 实际上我们已经画了整个框，用户说"边框：顶部1px solid..."
        # 我们可以画一条线在顶部
        border_color = QtGui.QColor(DesignTokens.COLORS['border'])
        border_color.setAlpha(100)
        painter.setPen(QtGui.QPen(border_color, 1))
        painter.drawLine(QtCore.QLineF(stats_rect.left(), stats_rect.top(), stats_rect.right(), stats_rect.top()))
        
        self._draw_statistics(
            painter, margin, timeline_y + 220, timeline_width)

    def _draw_header(self, painter: QtGui.QPainter, margin: int, header_height: int):
        """绘制精美的标题区域 - 已废弃，仅保留方法签名以防调用报错"""
        pass

    def _draw_time_scale(self, painter: QtGui.QPainter, margin: int, y: int, width: int):
        """绘制时间刻度"""
        painter.save()

        # 时间刻度
        # 文案：保持原"00:00 06:00 12:00 18:00 23:59" (虽然用户这么说，但代码里是 09:00-18:00，我保持代码原逻辑，只改样式)
        
        times = ["09:00", "10:00", "11:00", "12:00", "13:00",
                 "14:00", "15:00", "16:00", "17:00", "18:00"]
        
        # 莫兰迪蓝 70% -> 使用主题次要文字颜色 (金色/白色)
        painter.setPen(DesignTokens.COLORS['text_secondary']) 
        scale_font = QtGui.QFont("Segoe UI", 12) # 字体：保持原12px
        painter.setFont(scale_font)

        for i, time_str in enumerate(times):
            x = margin + (width * i / (len(times) - 1))

            # 绘制刻度线
            painter.setPen(DesignTokens.COLORS['border']) # 使用边框颜色 (绿色)
            painter.drawLine(int(x), y + 20, int(x), y + 30)

            # 绘制时间文字
            text_rect = painter.fontMetrics().boundingRect(time_str)
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x - text_rect.width()/2, y + 15, time_str, DesignTokens.COLORS['text_secondary'])

        painter.restore()

    def _draw_main_timeline(self, painter: QtGui.QPainter, margin: int, y: int, width: int):
        """绘制主时间轴线"""
        painter.save()

        # 主轴线渐变
        # 莫兰迪蓝 30% -> 金色 -> 莫兰迪蓝 30% -> 改为 绿色 -> 金色 -> 绿色
        line_gradient = QtGui.QLinearGradient(margin, y, margin + width, y)
        
        c_edge = QtGui.QColor(DesignTokens.COLORS['border'])
        c_edge.setAlpha(76)
        
        line_gradient.setColorAt(0, c_edge)
        line_gradient.setColorAt(0.5, QtGui.QColor("#5E8E79")) 
        line_gradient.setColorAt(1, c_edge)

        pen = QtGui.QPen()
        pen.setBrush(line_gradient)
        pen.setWidth(2) # 稍微变细一点，优雅
        painter.setPen(pen)
        painter.drawLine(margin, y, margin + width, y)
        
        # 移除之前的发光效果，保持通透
        
        painter.restore()

    def _draw_statistics(self, painter: QtGui.QPainter, margin: int, y: int, width: int):
        """绘制统计信息"""
        painter.save()
        stats_opacity = self.stats_anim.value
        if stats_opacity <= 0:
            stats_opacity = 1.0
        painter.setOpacity(stats_opacity)

        # 统计背景 - 透明或淡色边框
        stats_rect = QtCore.QRectF(margin, y, width, 120)
        
        # 背景 (10%透明)
        bg_color = QtGui.QColor(DesignTokens.COLORS['background'])
        bg_color.setAlpha(200) # Slightly more opaque for better readability
        painter.setBrush(bg_color)
        
        # 边框
        painter.setPen(QtGui.QPen(DesignTokens.COLORS['border'], 1))
        painter.drawRoundedRect(stats_rect, 12, 12)

        # 统计数据
        stats_data = [
            {"label": "总专注时长", "value": "6.5小时", "icon": "🎯",
                "color": "#5E8E79"},
            {"label": "专注效率", "value": "92%", "icon": "⚡",
                "color": DesignTokens.COLORS['text_primary']},
            {"label": "休息次数", "value": "3次", "icon": "☕",
                "color": DesignTokens.COLORS['text_primary']},
            {"label": "完成任务", "value": "8项", "icon": "✅",
                "color": "#5E8E79"}
        ]

        item_width = width / len(stats_data)
        for i, stat in enumerate(stats_data):
            x = margin + i * item_width + item_width / 2

            # 图标
            painter.setPen(DesignTokens.COLORS['text_secondary']) # 次要文字 (浅色)
            icon_font = QtGui.QFont("Segoe UI Emoji", 20)
            painter.setFont(icon_font)
            icon_rect = painter.fontMetrics().boundingRect(stat["icon"])
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x - icon_rect.width()/2, y + 35, stat["icon"], DesignTokens.COLORS['text_secondary'])

            # 数值
            painter.setPen(QtGui.QColor("#5E8E79"))
            value_font = QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold)
            painter.setFont(value_font)
            value_rect = painter.fontMetrics().boundingRect(stat["value"])
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x - value_rect.width()/2, y + 65, stat["value"], QtGui.QColor("#5E8E79"))

            # 标签
            painter.setPen(DesignTokens.COLORS['text_secondary']) # 次要文字 (浅色)
            label_font = QtGui.QFont("Segoe UI", 11)
            painter.setFont(label_font)
            label_rect = painter.fontMetrics().boundingRect(stat["label"])
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x - label_rect.width()/2, y + 85, stat["label"], DesignTokens.COLORS['text_secondary'])

        painter.restore()

    def _draw_timeline_entry(self, painter: QtGui.QPainter, entry: TimelineEntry, index: int,
                             margin: int, timeline_y: int, timeline_width: int,
                             animation_progress: float = 1.0, is_hovered: bool = False):
        """绘制精美的单个时间段"""
        start_minutes = self._time_to_minutes(entry.start_time)
        end_minutes = self._time_to_minutes(entry.end_time)

        # 映射到像素位置 (显示9:00-18:00的时间段)
        display_start = 9 * 60  # 9:00
        display_end = 18 * 60   # 18:00
        display_range = display_end - display_start

        x_start = margin + (start_minutes - display_start) / \
            display_range * timeline_width
        x_end = margin + (end_minutes - display_start) / \
            display_range * timeline_width

        painter.save()
        painter.setOpacity(animation_progress)

        hover_scale = 1.2 if is_hovered else 1.0
        base_height = 40
        segment_height = base_height * hover_scale * animation_progress
        segment_y_offset = (base_height - segment_height) / 2

        if is_hovered:
            glow_rect = QtCore.QRectF(x_start - 5, timeline_y - 20 + segment_y_offset - 5,
                                      (x_end - x_start) * animation_progress + 10, segment_height + 10)
            glow_color = QtGui.QColor(entry.color)
            glow_color.setAlpha(int(100 * animation_progress))
            painter.setBrush(glow_color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawRoundedRect(glow_rect, 8, 8)

        shadow_rect = QtCore.QRectF(x_start + 3, timeline_y - 20 + segment_y_offset + 3,
                                    (x_end - x_start) * animation_progress, segment_height)
        shadow_color = QtGui.QColor(0, 0, 0, int(40 * animation_progress))
        painter.setBrush(shadow_color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)

        segment_rect = QtCore.QRectF(x_start, timeline_y - 20 + segment_y_offset,
                                     (x_end - x_start) * animation_progress, segment_height)

        if entry.activity_type == "work":
            fill_color = QtGui.QColor("#FFD54F")
            border_color = QtGui.QColor("#FFA000")
        elif entry.activity_type == "rest":
            fill_color = QtGui.QColor("#4FC3F7")
            border_color = QtGui.QColor("#0288D1")
        else:
            fill_color = QtGui.QColor("#A5D6A7")
            border_color = QtGui.QColor("#2E7D32")

        painter.setBrush(fill_color)
        painter.setPen(QtGui.QPen(border_color, 1))
        painter.drawRoundedRect(segment_rect, 8, 8)

        if animation_progress > 0.5:
            icon_alpha = (animation_progress - 0.5) / 0.5
            painter.setOpacity(icon_alpha)

            icon_x = x_start + 10
            icon_y = timeline_y - 10

            if entry.activity_type == "work":
                icon = "💻"
            elif entry.activity_type == "rest":
                icon = "🍽️"
            else:  # break
                icon = "☕"

            painter.setPen(QtGui.QColor(255, 255, 255))
            icon_font = QtGui.QFont("Segoe UI Emoji", 16)
            painter.setFont(icon_font)
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, icon_x, icon_y, icon, QtGui.QColor(255, 255, 255))

        # 绘制时间标签和描述（动画完成70%后显示）- 修复重叠问题
        if animation_progress > 0.7:
            text_alpha = (animation_progress - 0.7) / 0.3
            painter.setOpacity(text_alpha)

            # 计算每个时间段的垂直偏移，避免重叠
            vertical_offset = (index % 2) * 60  # 奇偶交替显示位置

            # 时间标签 - 调整位置避免重叠
            time_text = f"{entry.start_time}-{entry.end_time}"
            time_font = QtGui.QFont("Segoe UI", 11, QtGui.QFont.Bold)
            painter.setFont(time_font)

            # 时间文字 - 根据索引调整位置
            painter.setPen(QtGui.QColor("#a8d8ea")) # 标题蓝色
            time_y = timeline_y - 50 - vertical_offset
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x_start, time_y, time_text, QtGui.QColor("#a8d8ea"))

            # 描述文字 - 智能换行和位置调整
            desc_font = QtGui.QFont("Segoe UI", 10)
            painter.setFont(desc_font)
            painter.setPen(QtGui.QColor("#F9A825")) # 数值金色

            # 限制描述文字长度，避免重叠
            max_width = min(200, int(x_end - x_start))
            desc_text = entry.description

            # 如果文字太长，进行智能截断
            if painter.fontMetrics().boundingRect(desc_text).width() > max_width:
                # 截断文字并添加省略号
                while painter.fontMetrics().boundingRect(desc_text + "...").width() > max_width and len(desc_text) > 10:
                    desc_text = desc_text[:-1]
                desc_text += "..."

            desc_y = timeline_y + 35 + vertical_offset
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, x_start, desc_y, desc_text, QtGui.QColor("#F9A825"))

        # 绘制持续时长指示器 - 调整位置避免重叠
        if animation_progress > 0.8:
            duration_minutes = end_minutes - start_minutes
            duration_text = f"{duration_minutes}分钟"

            painter.setOpacity((animation_progress - 0.8) / 0.2)
            painter.setPen(MorandiTheme.COLOR_TEXT_SUBTITLE)
            duration_font = QtGui.QFont("Segoe UI", 9)
            painter.setFont(duration_font)

            # 将持续时长显示在时间段条的中央
            duration_x = x_start + (x_end - x_start) * animation_progress / 2
            duration_rect = painter.fontMetrics().boundingRect(duration_text)
            duration_y = timeline_y + 5  # 显示在时间段条内部
            
            # 使用更深的阴影以确保在亮色背景上可见
            shadow_color = QtGui.QColor(0, 0, 0, 160)
            MorandiTheme.draw_text_at_point_with_shadow(
                painter, duration_x - duration_rect.width()/2, duration_y, duration_text, 
                MorandiTheme.COLOR_TEXT_SUBTITLE, shadow_color)

        painter.restore()

    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    def mousePressEvent(self, event):
        """鼠标按下事件 - 处理拖拽"""
        if event.button() == QtCore.Qt.LeftButton:
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            self.drag_pos = pos - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 实现悬停效果和窗口拖拽"""
        # 处理窗口拖拽
        if event.buttons() & QtCore.Qt.LeftButton and hasattr(self, 'drag_pos'):
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            self.move(pos - self.drag_pos)
            event.accept()
            return

        super().mouseMoveEvent(event)

        # 检查鼠标是否悬停在时间段上
        margin = 80
        timeline_y = 340  # header_height + 180 (更新后的位置)
        timeline_width = self.width() - 2 * margin

        old_hover = self.hover_segment
        self.hover_segment = -1

        for i, entry in enumerate(self.timeline_entries):
            start_minutes = self._time_to_minutes(entry.start_time)
            end_minutes = self._time_to_minutes(entry.end_time)

            display_start = 9 * 60  # 9:00
            display_end = 18 * 60   # 18:00
            display_range = display_end - display_start

            x_start = margin + (start_minutes - display_start) / \
                display_range * timeline_width
            x_end = margin + (end_minutes - display_start) / \
                display_range * timeline_width

            # 检查鼠标是否在时间段范围内
            if (x_start <= event.x() <= x_end and
                    timeline_y - 30 <= event.y() <= timeline_y + 30):
                self.hover_segment = i
                break

        # 如果悬停状态改变，触发重绘
        if old_hover != self.hover_segment:
            self.update()

    def leaveEvent(self, event):
        """鼠标离开事件"""
        super().leaveEvent(event)
        if self.hover_segment != -1:
            self.hover_segment = -1
            self.update()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止粒子定时器
        if self.particle_timer.isActive():
            self.particle_timer.stop()

        # 停止入场粒子效果
        if hasattr(self, 'entrance_particle_effect'):
            self.entrance_particle_effect.stop()

        super().closeEvent(event)


class EnhancedParticleEffect(ParticleEffect):
    """增强的粒子效果系统"""

    def create_celebration_burst(self, center: QtCore.QPoint, intensity: int = 15):
        """创建庆祝爆炸效果"""
        self.create_celebration_particles(center, intensity)

    def create_success_sparkles(self, center: QtCore.QPoint):
        """创建成功闪烁效果"""
        self.particles.clear()

        # 创建闪烁粒子
        for i in range(8):
            angle = (360 / 8) * i
            distance = 30 + random.random() * 20

            x = center.x() + math.cos(math.radians(angle)) * distance
            y = center.y() + math.sin(math.radians(angle)) * distance

            particle = {
                'x': float(x),
                'y': float(y),
                'vx': 0,
                'vy': 0,
                'life': 1.0,
                'max_life': 1.0,
                'size': 4 + random.random() * 3,
                'color': DesignTokens.COLORS['accent'],
                'rotation': 0,
                'rotation_speed': (random.random() - 0.5) * 15
            }
            self.particles.append(particle)

        if not self.is_active:
            self.is_active = True
            self.timer.start(16)

    def create_expand_explosion(self, center: QtCore.QPoint):
        """创建展开爆炸效果"""
        print(f"创建展开爆炸效果，粒子数量: 25，位置: {center}")  # 调试信息
        self.particles.clear()

        # 创建向外扩散的粒子 - 增加数量和持续时间
        for i in range(25):
            angle = random.random() * 360
            speed = 2 + random.random() * 5  # 增加速度范围

            particle = {
                'x': float(center.x()),
                'y': float(center.y()),
                'vx': math.cos(math.radians(angle)) * speed,
                'vy': math.sin(math.radians(angle)) * speed,
                'life': 1.5,  # 增加生命值，让粒子持续更久
                'max_life': 1.5,
                'size': 3 + random.random() * 5,  # 增加粒子大小
                'color': self._get_celebration_colors()[i % len(self._get_celebration_colors())],
                'rotation': 0,
                'rotation_speed': (random.random() - 0.5) * 15
            }
            self.particles.append(particle)

        print(f"创建了 {len(self.particles)} 个展开粒子")  # 调试信息

        if not self.is_active:
            self.is_active = True
            self.timer.start(16)
            print("启动展开粒子动画定时器")  # 调试信息

    def create_golden_sparkle_shower(self, widget_rect: QtCore.QRect):
        """创建金色粒子雨效果 - 类似图片中的效果"""
        print(f"创建金色粒子雨效果，覆盖区域: {widget_rect}")  # 调试信息
        self.particles.clear()

        # 创建大量金色粒子，分布在整个界面
        particle_count = 80  # 增加粒子数量以获得更丰富的效果

        for i in range(particle_count):
            # 随机分布在整个界面区域
            x = widget_rect.left() + random.random() * widget_rect.width()
            y = widget_rect.top() + random.random() * widget_rect.height()

            # 创建不同大小的粒子以增加层次感
            size_category = random.random()
            if size_category < 0.3:  # 30% 小粒子
                size = 1 + random.random() * 2
                life_time = 1.5 + random.random() * 0.5
            elif size_category < 0.7:  # 40% 中等粒子
                size = 2 + random.random() * 3
                life_time = 2.0 + random.random() * 0.5
            else:  # 30% 大粒子
                size = 3 + random.random() * 4
                life_time = 2.5 + random.random() * 0.5

            # 轻微的随机运动
            vx = (random.random() - 0.5) * 0.8  # 水平漂移
            vy = (random.random() - 0.5) * 0.6  # 垂直漂移

            particle = {
                'x': float(x),
                'y': float(y),
                'vx': vx,
                'vy': vy,
                'life': life_time,
                'max_life': life_time,
                'size': size,
                'color': self._get_golden_colors()[i % len(self._get_golden_colors())],
                'rotation': random.random() * 360,
                'rotation_speed': (random.random() - 0.5) * 8,
                'twinkle_phase': random.random() * math.pi * 2,  # 闪烁相位
                'twinkle_speed': 2 + random.random() * 3  # 闪烁速度
            }
            self.particles.append(particle)

        print(f"创建了 {len(self.particles)} 个金色粒子")  # 调试信息

        if not self.is_active:
            self.is_active = True
            self.timer.start(16)
            print("启动金色粒子雨动画定时器")  # 调试信息

    def create_timeline_entrance_effect(self):
        """创建时间轴打开时的特殊粒子效果"""
        print("创建时间轴入场粒子效果")  # 调试信息
        self.particles.clear()

        # 创建从中心向外扩散的金色粒子
        center_x = 500  # 时间轴窗口中心
        center_y = 350

        for i in range(60):  # 更多粒子用于时间轴效果
            # 创建螺旋扩散效果
            angle = (i * 15) % 360 + random.random() * 30  # 螺旋角度
            distance = 50 + (i * 8)  # 递增距离

            x = center_x + math.cos(math.radians(angle)) * (distance * 0.3)
            y = center_y + math.sin(math.radians(angle)) * (distance * 0.3)

            # 向外扩散的速度
            speed = 1.5 + random.random() * 2.5
            vx = math.cos(math.radians(angle)) * speed
            vy = math.sin(math.radians(angle)) * speed

            particle = {
                'x': float(x),
                'y': float(y),
                'vx': vx,
                'vy': vy,
                'life': 2.0 + random.random() * 1.0,
                'max_life': 2.0 + random.random() * 1.0,
                'size': 2 + random.random() * 4,
                'color': self._get_golden_colors()[i % len(self._get_golden_colors())],
                'rotation': 0,
                'rotation_speed': (random.random() - 0.5) * 12,
                'twinkle_phase': random.random() * math.pi * 2,
                'twinkle_speed': 3 + random.random() * 2
            }
            self.particles.append(particle)

        if not self.is_active:
            self.is_active = True
            self.timer.start(16)

    def _get_golden_colors(self):
        """获取金色系粒子颜色"""
        return [
            '#FFD700',  # 金色
            '#FFA500',  # 橙色
            '#FFFF00',  # 黄色
            '#FFE55C',  # 浅金色
            '#FFC125',  # 深金色
            '#DAA520',  # 暗金色
            '#F0E68C',  # 卡其色
            '#FFEB3B',  # 亮黄色
            '#FFF176',  # 浅黄色
        ]

    def _get_celebration_colors(self):
        """获取庆祝颜色列表"""
        return [
            DesignTokens.COLORS['accent'],
            DesignTokens.COLORS['primary'],
            DesignTokens.COLORS['secondary'],
            '#ff6b6b',  # 红色
            '#4ecdc4',  # 青色
            '#45b7d1',  # 蓝色
            '#f9ca24',  # 黄色
            '#ff9ff3',  # 粉色
            '#54a0ff',  # 天蓝色
        ]

    def update_particles(self):
        """优化的粒子状态更新 - 增强版"""
        if not self.particles:
            self.timer.stop()
            self.is_active = False
            return

        updated_particles = []

        for particle in self.particles:
            # 更新位置
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']

            # 轻微的重力和阻力效果
            particle['vy'] += 0.08  # 减少重力以获得更飘逸的效果
            particle['vx'] *= 0.995  # 减少阻力
            particle['vy'] *= 0.995

            # 更新生命值 - 更慢的衰减
            life_decay = 0.006 + (particle['size'] - 1) * 0.0008
            particle['life'] -= life_decay

            # 更新旋转
            particle['rotation'] += particle['rotation_speed']

            # 更新闪烁效果
            if 'twinkle_phase' in particle:
                particle['twinkle_phase'] += particle['twinkle_speed'] * 0.1

            # 添加轻微的随机扰动
            if random.random() < 0.05:  # 降低扰动频率
                particle['vx'] += (random.random() - 0.5) * 0.1
                particle['vy'] += (random.random() - 0.5) * 0.1

            # 只保留活着的粒子
            if particle['life'] > 0:
                updated_particles.append(particle)

        self.particles = updated_particles

        # 触发重绘
        if self.particles and self.parent:
            self.parent.update()
        elif not self.particles:
            self.timer.stop()
            self.is_active = False

    def draw_particles(self, painter):
        """绘制增强的粒子效果"""
        if not self.particles:
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        alive_particles = [p for p in self.particles if p['life'] > 0]
        if not alive_particles:
            painter.restore()
            return

        # 按生命值排序
        alive_particles.sort(key=lambda p: p['life'])

        for particle in alive_particles:
            alpha_factor = particle['life'] / particle['max_life']

            # 闪烁效果
            twinkle_factor = 1.0
            if 'twinkle_phase' in particle:
                twinkle_factor = 0.7 + 0.3 * \
                    math.sin(particle['twinkle_phase'])

            current_size = particle['size'] * twinkle_factor
            x, y = int(particle['x']), int(particle['y'])

            if alpha_factor < 0.01:
                continue

            # 创建更丰富的渐变效果
            gradient = QtGui.QRadialGradient(x, y, current_size / 2)

            core_color = QtGui.QColor(particle['color'])
            core_color.setAlpha(int(255 * alpha_factor * twinkle_factor))

            edge_color = QtGui.QColor(particle['color'])
            edge_color.setAlpha(int(120 * alpha_factor * twinkle_factor))

            gradient.setColorAt(0, core_color)
            gradient.setColorAt(0.6, edge_color)
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))

            # 绘制发光效果
            if alpha_factor > 0.2:
                glow_size = current_size * 2.2
                glow_gradient = QtGui.QRadialGradient(x, y, glow_size / 2)

                glow_color = QtGui.QColor(particle['color'])
                glow_color.setAlpha(int(40 * alpha_factor * twinkle_factor))

                glow_gradient.setColorAt(0, glow_color)
                glow_gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 0))

                painter.setBrush(glow_gradient)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(
                    int(x - glow_size / 2), int(y - glow_size / 2),
                    int(glow_size), int(glow_size)
                )

            # 绘制主粒子
            painter.setBrush(gradient)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(
                int(x - current_size / 2), int(y - current_size / 2),
                int(current_size), int(current_size)
            )

            # 添加星形闪烁效果
            if random.random() < 0.15 * alpha_factor * twinkle_factor:
                sparkle_size = current_size * 0.4
                sparkle_color = QtGui.QColor(
                    255, 255, 255, int(180 * alpha_factor))
                painter.setBrush(sparkle_color)
                painter.drawEllipse(
                    int(x - sparkle_size / 2), int(y - sparkle_size / 2),
                    int(sparkle_size), int(sparkle_size)
                )

        painter.restore()


class ParticleOverlay(QtWidgets.QWidget):
    """粒子效果覆盖层 - 确保粒子效果在最顶层显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particle_effect = None

        # 设置为透明背景，不接受鼠标事件
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        # 确保覆盖层始终在最顶层
        self.raise_()

    def set_particle_effect(self, particle_effect):
        """设置要显示的粒子效果"""
        self.particle_effect = particle_effect

    def update_geometry(self):
        """更新覆盖层几何位置以匹配父窗口"""
        if self.parent():
            self.setGeometry(self.parent().rect())
            self.raise_()  # 确保始终在最顶层

    def paintEvent(self, event):
        """绘制粒子效果"""
        if not self.particle_effect or not self.particle_effect.particles:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        # 绘制粒子效果
        self.particle_effect.draw_particles(painter)

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self.update_geometry()

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.update_geometry()


class MotivationalFooter(QtWidgets.QWidget):
    """励志文字区域组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.message = "加油！今天又是努力的一天呢！"
        self.collapsed_mode = True
        self.setFixedHeight(60)

        # 动画效果
        self.glow_anim = AnimatedValue(0.0)
        self.glow_anim.valueChanged.connect(self.update)

        # 启动发光动画
        self._start_glow_animation()

    def set_message(self, message: str):
        """设置励志文字"""
        self.message = message
        self.update()

    def update_style(self, collapsed_mode: bool):
        """更新样式以适应不同模式"""
        self.collapsed_mode = collapsed_mode
        self._check_layout_integrity()
        self.update()

    def _check_layout_integrity(self):
        """检查布局完整性，确保文字不与其他元素重叠"""
        if not self.parent():
            return

        parent_rect = self.parent().rect()
        my_rect = self.geometry()

        # 检查是否超出父容器边界
        if my_rect.bottom() > parent_rect.bottom():
            # 调整位置以避免超出边界
            new_y = parent_rect.bottom() - my_rect.height() - 10
            self.move(my_rect.x(), max(0, new_y))

        # 检查与兄弟组件的重叠
        self._avoid_sibling_overlap()

    def _avoid_sibling_overlap(self):
        """避免与兄弟组件重叠"""
        if not self.parent():
            return

        parent = self.parent()
        my_rect = self.geometry()

        # 获取所有兄弟组件
        siblings = [child for child in parent.children()
                    if isinstance(child, QtWidgets.QWidget) and child != self and child.isVisible()]

        for sibling in siblings:
            sibling_rect = sibling.geometry()

            # 检查是否重叠
            if my_rect.intersects(sibling_rect):
                # 计算最小移动距离以避免重叠
                overlap_rect = my_rect.intersected(sibling_rect)

                # 优先向下移动
                if overlap_rect.height() < overlap_rect.width():
                    new_y = sibling_rect.bottom() + 5
                    if new_y + my_rect.height() <= parent.rect().bottom():
                        self.move(my_rect.x(), new_y)
                    else:
                        # 如果向下移动会超出边界，则向上移动
                        new_y = sibling_rect.top() - my_rect.height() - 5
                        self.move(my_rect.x(), max(0, new_y))

    def resizeEvent(self, event):
        """窗口大小改变时重新检查布局"""
        super().resizeEvent(event)
        QtCore.QTimer.singleShot(0, self._check_layout_integrity)

    def _start_glow_animation(self):
        """启动发光动画"""
        def animate_glow():
            self.glow_anim.animate_to(
                1.0, 2000, 0, DesignTokens.EASINGS['ease_in_out'])
            QtCore.QTimer.singleShot(2000, lambda: self.glow_anim.animate_to(
                0.3, 2000, 0, DesignTokens.EASINGS['ease_in_out']))
            QtCore.QTimer.singleShot(4000, animate_glow)

        animate_glow()

    def paintEvent(self, event):
        """绘制励志文字"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()

        # 绘制背景渐变
        gradient = QtGui.QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QtGui.QColor(255, 255, 255, 0))

        accent_color = QtGui.QColor(DesignTokens.COLORS['accent_light'])
        accent_color.setAlphaF(0.1)
        gradient.setColorAt(1, accent_color)

        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRect(rect)

        # 绘制励志文字
        painter.setPen(QtGui.QColor(DesignTokens.COLORS['text_primary']))

        # 添加发光效果
        if self.glow_anim.value > 0:
            glow_color = QtGui.QColor(DesignTokens.COLORS['accent'])
            glow_color.setAlphaF(0.3 * self.glow_anim.value)
            painter.setPen(glow_color)

        font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Medium)
        painter.setFont(font)

        # 居中绘制文字
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.message)

# --- 现代化卡片组件 ---


class Card1_Focus(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(130)  # 增加高度
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 动画值
        self.progress_val = AnimatedValue(0.0)
        self.progress_val.valueChanged.connect(self.update)

        self.slide_anim_val = AnimatedValue(0.0)
        self.slide_anim_val.valueChanged.connect(self.update)

        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        self.glow_intensity = AnimatedValue(0.0)
        self.glow_intensity.valueChanged.connect(self.update)

        # 粒子效果
        self.particle_effect = ParticleEffect(self)

        # 启动动画序列
        self.start_animations()

    def start_animations(self):
        """启动错开的入场动画"""
        # 滑入动画: 延迟400ms
        self.slide_anim_val.animate_to(
            1.0, 300, 400, DesignTokens.EASINGS['ease_out'])

        # 进度条动画: 延迟700ms，使用弹性效果
        self.progress_val.animate_to(
            0.5625, 800, 700, DesignTokens.EASINGS['back'])

        # 发光效果: 延迟1000ms
        self.glow_intensity.animate_to(
            1.0, 500, 1000, DesignTokens.EASINGS['ease_in_out'])

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = self.rect()

        # 绘制悬停发光效果
        if self.hover_progress.value > 0:
            glow_rect = rect.adjusted(-2, -2, 2, 2)
            glow_color = QtGui.QColor(DesignTokens.COLORS['primary'])
            glow_color.setAlphaF(0.3 * self.hover_progress.value)
            p.setBrush(glow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(glow_rect, 8, 8)

        # 绘制背景 - 透明 (让星空背景透出来)
        # p.setBrush(QtCore.Qt.NoBrush)
        # p.setPen(QtCore.Qt.NoPen)
        # p.drawRoundedRect(rect, 6, 6)

        # 绘制左侧装饰条
        accent_rect = QtCore.QRectF(0, 0, 4, rect.height())
        accent_gradient = QtGui.QLinearGradient(0, 0, 0, rect.height())
        accent_gradient.setColorAt(
            0, QtGui.QColor(DesignTokens.COLORS['primary']))
        accent_gradient.setColorAt(1, QtGui.QColor(
            DesignTokens.COLORS['primary_light']))
        p.setBrush(accent_gradient)
        p.drawRoundedRect(accent_rect, 2, 2)

        # 标题 - 使用更现代的字体和颜色
        p.setPen(QtGui.QColor("#A05C3B"))
        title_font = QtGui.QFont("Segoe UI", 10, QtGui.QFont.Medium)
        p.setFont(title_font)
        p.drawText(20, 28, "🎯 今日专注时长")

        # 主数字 - 增强视觉效果
        p.setPen(QtGui.QColor(DesignTokens.COLORS['accent']))
        main_font = QtGui.QFont("Segoe UI", 28, QtGui.QFont.Bold)
        p.setFont(main_font)

        # 添加数字阴影效果
        shadow_color = QtGui.QColor(DesignTokens.COLORS['accent'])
        shadow_color.setAlpha(50)
        p.setPen(shadow_color)
        p.drawText(22, 67, "4.5小时")

        # 主数字
        p.setPen(QtGui.QColor(DesignTokens.COLORS['accent']))
        p.drawText(20, 65, "4.5小时")

        # 滑入的增长指示器 - 重新设计
        slide_progress = self.slide_anim_val.value
        if slide_progress > 0:
            p.setOpacity(slide_progress)
            x_offset = (1.0 - slide_progress) * 30

            # 绘制增长标签背景
            label_rect = QtCore.QRectF(140 + x_offset, 45, 120, 25)
            label_gradient = QtGui.QLinearGradient(
                label_rect.topLeft(), label_rect.bottomLeft())
            label_gradient.setColorAt(0, QtGui.QColor(
                DesignTokens.COLORS['secondary']))
            label_gradient.setColorAt(1, QtGui.QColor(39, 174, 96))  # 深绿色
            p.setBrush(label_gradient)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(label_rect, 12, 12)

            # 增长文字
            p.setPen(QtGui.QColor("white"))
            growth_font = QtGui.QFont("Segoe UI", 9, QtGui.QFont.Medium)
            p.setFont(growth_font)
            p.drawText(label_rect, QtCore.Qt.AlignCenter, "↗ +30分钟")
            p.setOpacity(1.0)

        # 现代化进度条
        bar_rect = QtCore.QRectF(20, 95, rect.width() - 40, 8)

        # 进度条背景 - 暗色主题
        p.setBrush(QtGui.QColor(DesignTokens.COLORS['border']))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(bar_rect, 4, 4)

        # 进度条前景 - 渐变效果
        prog = self.progress_val.value
        if prog > 0:
            fill_width = bar_rect.width() * prog
            fill_rect = QtCore.QRectF(20, 95, fill_width, 8)

            # 创建进度条渐变
            progress_gradient = QtGui.QLinearGradient(
                fill_rect.topLeft(), fill_rect.topRight())
            progress_gradient.setColorAt(
                0, QtGui.QColor(DesignTokens.COLORS['primary']))
            progress_gradient.setColorAt(1, QtGui.QColor(
                DesignTokens.COLORS['primary_light']))

            p.setBrush(progress_gradient)
            p.drawRoundedRect(fill_rect, 4, 4)

            # 进度条发光效果
            if self.glow_intensity.value > 0:
                glow_rect = fill_rect.adjusted(-1, -1, 1, 1)
                glow_color = QtGui.QColor(DesignTokens.COLORS['primary'])
                glow_color.setAlphaF(0.4 * self.glow_intensity.value)
                p.setBrush(glow_color)
                p.drawRoundedRect(glow_rect, 5, 5)

        # 进度百分比文字
        if prog > 0.1:  # 只在有足够进度时显示
            p.setPen(QtGui.QColor(DesignTokens.COLORS['text_muted']))
            percent_font = QtGui.QFont("Segoe UI", 8)
            p.setFont(percent_font)
            percent_text = f"{int(prog * 100)}%"
            p.drawText(rect.width() - 35, 115, percent_text)

        # 绘制粒子效果
        self.particle_effect.draw_particles(p)

    def enterEvent(self, event):
        """鼠标进入事件"""
        self.hover_progress.animate_to(
            1.0, 200, 0, DesignTokens.EASINGS['ease_out'])

    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.hover_progress.animate_to(
            0.0, 200, 0, DesignTokens.EASINGS['ease_out'])

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == QtCore.Qt.LeftButton:
            # 创建庆祝粒子效果
            center = QtCore.QPoint(self.width() // 2, self.height() // 2)
            print(f"点击卡片，创建粒子效果在位置: {center}")  # 调试信息
            self.particle_effect.create_celebration_particles(center, 12)

            # 立即触发重绘以显示粒子
            self.update()

            # 点击缩放动画
            scale_anim = QtCore.QPropertyAnimation(self, b"geometry")
            original_geo = self.geometry()
            scaled_geo = QtCore.QRect(
                original_geo.x() + 2, original_geo.y() + 2,
                original_geo.width() - 4, original_geo.height() - 4
            )
            scale_anim.setDuration(100)
            scale_anim.setStartValue(original_geo)
            scale_anim.setEndValue(scaled_geo)
            scale_anim.setEasingCurve(DesignTokens.EASINGS['ease_out'])

            # 恢复动画
            def restore_size():
                restore_anim = QtCore.QPropertyAnimation(self, b"geometry")
                restore_anim.setDuration(100)
                restore_anim.setStartValue(scaled_geo)
                restore_anim.setEndValue(original_geo)
                restore_anim.setEasingCurve(DesignTokens.EASINGS['bounce'])
                restore_anim.start()

            scale_anim.finished.connect(restore_size)
            scale_anim.start()

            scale_anim.finished.connect(restore_size)
            scale_anim.start()
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
        self.setFixedHeight(90)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 动画值
        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        self.dots_anim = AnimatedValue(0.0)
        self.dots_anim.valueChanged.connect(self.update)

        # 启动圆点动画
        QtCore.QTimer.singleShot(600, lambda: self.dots_anim.animate_to(
            1.0, 800, 0, DesignTokens.EASINGS['bounce']))

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()

        # 悬停效果背景
        if self.hover_progress.value > 0:
            hover_color = QtGui.QColor(DesignTokens.COLORS['secondary'])
            hover_color.setAlphaF(0.1 * self.hover_progress.value)
            p.setBrush(hover_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(rect, 6, 6)

        # 标题
        p.setPen(QtGui.QColor("#A05C3B"))
        title_font = QtGui.QFont("Segoe UI", 10, QtGui.QFont.Medium)
        p.setFont(title_font)
        p.drawText(20, 25, "🔔 今日分心次数")

        # 主数字
        p.setPen(QtGui.QColor("#6A4A3F"))
        main_font = QtGui.QFont("Segoe UI", 18, QtGui.QFont.Bold)
        p.setFont(main_font)
        p.drawText(120, 28, "7次")

        # 改进指示器 - 带背景的标签
        improvement_rect = QtCore.QRectF(200, 15, 80, 20)
        improvement_gradient = QtGui.QLinearGradient(
            improvement_rect.topLeft(), improvement_rect.bottomLeft())
        improvement_gradient.setColorAt(
            0, QtGui.QColor(DesignTokens.COLORS['secondary']))
        improvement_gradient.setColorAt(1, QtGui.QColor(39, 174, 96))
        p.setBrush(improvement_gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(improvement_rect, 10, 10)

        p.setPen(QtGui.QColor("white"))
        improvement_font = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Medium)
        p.setFont(improvement_font)
        p.drawText(improvement_rect, QtCore.Qt.AlignCenter, "↓ -2次")

        # 现代化圆点指示器
        dot_y = 55
        dot_size = 10
        spacing = 16
        start_x = 20

        # 数据：5个成功控制，2个分心
        dot_data = [
            {'color': DesignTokens.COLORS['warning'], 'type': 'distraction'},
            {'color': DesignTokens.COLORS['warning'], 'type': 'distraction'},
            {'color': DesignTokens.COLORS['warning'], 'type': 'distraction'},
            {'color': DesignTokens.COLORS['warning'], 'type': 'distraction'},
            {'color': DesignTokens.COLORS['warning'], 'type': 'distraction'},
            {'color': DesignTokens.COLORS['secondary'], 'type': 'success'},
            {'color': DesignTokens.COLORS['secondary'], 'type': 'success'}
        ]

        for i, dot in enumerate(dot_data):
            # 动画延迟
            delay_progress = max(0, min(1, (self.dots_anim.value * 7 - i) / 1))
            if delay_progress <= 0:
                continue

            x = start_x + i * spacing

            # 圆点阴影
            shadow_color = QtGui.QColor(dot['color'])
            shadow_color.setAlpha(50)
            p.setBrush(shadow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(QtCore.QRectF(x + 1, dot_y + 1, dot_size, dot_size))

            # 主圆点
            dot_color = QtGui.QColor(dot['color'])
            dot_color.setAlphaF(delay_progress)
            p.setBrush(dot_color)

            # 添加发光效果
            if dot['type'] == 'success':
                glow_size = dot_size + 4
                glow_color = QtGui.QColor(dot['color'])
                glow_color.setAlphaF(0.3 * delay_progress)
                p.setBrush(glow_color)
                p.drawEllipse(QtCore.QRectF(x - 2, dot_y - 2, glow_size, glow_size))

            # 绘制主圆点
            p.setBrush(dot_color)
            current_size = dot_size * delay_progress
            offset = (dot_size - current_size) / 2
            p.drawEllipse(QtCore.QRectF(x + offset, dot_y + offset,
                          current_size, current_size))

    def enterEvent(self, event):
        self.hover_progress.animate_to(
            1.0, 200, 0, DesignTokens.EASINGS['ease_out'])

    def leaveEvent(self, event):
        self.hover_progress.animate_to(
            0.0, 200, 0, DesignTokens.EASINGS['ease_out'])


class Card3_Flow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # 标题 - 暗色主题
        p.setPen(QtGui.QColor("#6A4A3F"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "⚡ 最长心流时段")

        # 内容 - 暗色主题
        p.setPen(QtGui.QColor("#5E8E79"))
        p.setFont(QtGui.QFont("Noto Sans SC", 12, QtGui.QFont.Bold))
        p.drawText(20, 50, "92分钟")
        p.setPen(QtGui.QColor("#A05C3B"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(100, 50, "（约1.5小时） 9:30-11:02")

        # 时间轴
        line_y = 75
        margin_x = 20
        w = self.width() - margin_x * 2

        # 轴线 - 暗色主题
        p.setPen(QtGui.QPen(QtGui.QColor(DesignTokens.COLORS['border']), 1))
        p.drawLine(margin_x, line_y, margin_x + w, line_y)

        # 刻度 - 暗色主题
        times = ["00:00", "06:00", "12:00", "18:00", "23:59"]
        p.setPen(QtGui.QColor("#A05C3B"))
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

        p.setBrush(QtGui.QColor(DesignTokens.COLORS['warning']))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRect(QtCore.QRectF(x1, line_y - 4, x2-x1, 8))


class Card4_Rest(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # 标题 - 暗色主题
        p.setPen(QtGui.QColor("#A05C3B"))
        p.setFont(QtGui.QFont("Noto Sans SC", 9))
        p.drawText(20, 25, "🛋️ 休息达标率")

        # 内容 - 暗色主题
        p.setPen(QtGui.QColor("#5E8E79"))
        p.setFont(QtGui.QFont("Noto Sans SC", 16, QtGui.QFont.Bold))
        p.drawText(120, 25, "85%")

        # 星星
        # ★★★★☆
        star_size = 16
        spacing = 20
        start_x = 20
        y = 45

        font_star = QtGui.QFont("Segoe UI Emoji", 14)  # Or similar
        p.setFont(font_star)

        for i in range(5):
            if i < 4:
                p.setPen(QtGui.QColor(DesignTokens.COLORS['accent']))  # 青绿色
                txt = "★"
            else:
                p.setPen(QtGui.QColor(DesignTokens.COLORS['text_muted']))  # 灰色
                txt = "☆"  # Or solid grey star

            p.drawText(start_x + i*spacing, y + star_size, txt)

# --- 主窗口 ---


class StarryCardWidget(QtWidgets.QWidget):
    """星空背景卡片组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardWidget")
        
        # 星星数据
        self.stars = self._init_stars()
        self.shooting_star = None
        
        # 动画定时器
        self.anim_timer = QtCore.QTimer(self)
        self.anim_timer.timeout.connect(self.update_animations)
        self.anim_timer.start(50) # 20 FPS
        
        # 流星定时器
        QtCore.QTimer.singleShot(2000, self.spawn_shooting_star)

    def _init_stars(self):
        stars = []
        # 主星 (3颗)
        stars.append({'type': 'main', 'x': 20, 'y': 20, 'size': 2, 'delay': 0})
        stars.append({'type': 'main', 'x': 400, 'y': 40, 'size': 2, 'delay': 0.5})
        stars.append({'type': 'main', 'x': 380, 'y': 800, 'size': 2, 'delay': 1.0})
        
        # 背景星星 (5颗)
        for _ in range(5):
            stars.append({
                'type': 'bg', 
                'x': random.randint(10, 440), 
                'y': random.randint(10, 850), 
                'size': 1, 
                'delay': random.random()*5
            })
        return stars

    def spawn_shooting_star(self):
        # 从左上到右下
        self.shooting_star = {
            'start_x': 20, 'start_y': 20, 
            'end_x': 400, 'end_y': 600, 
            'progress': 0.0
        }
        # 4秒后再次发射
        QtCore.QTimer.singleShot(4000 + int(random.random() * 2000), self.spawn_shooting_star)

    def update_animations(self):
        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0
        
        # 更新星星
        for star in self.stars:
            if star['type'] == 'main':
                # 2秒周期: 0.8 -> 1 -> 0.8
                t = (current_time + star['delay']) % 2.0
                norm = t / 1.0 if t < 1.0 else (2.0 - t) / 1.0
                star['alpha'] = 204 + (51 * norm) # 0.8 到 1.0
            else:
                # 8秒周期: 0.15 -> 0.25 -> 0.15
                t = (current_time + star['delay']) % 8.0
                norm = t / 4.0 if t < 4.0 else (8.0 - t) / 4.0
                star['alpha'] = 38 + (26 * norm) # 约 15% 到 25%
                
        # 更新流星
        if self.shooting_star:
            self.shooting_star['progress'] += 0.0125 # 4秒完成
            if self.shooting_star['progress'] >= 1.0:
                self.shooting_star = None
                
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QtGui.QColor("#D4E0BB"))
        gradient.setColorAt(1, QtGui.QColor("#E0E1AC"))
        
        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 12, 12)
        
        # 2. 模拟噪声纹理 (简单随机点 - 保持但更淡)
        painter.setPen(QtGui.QColor(255, 255, 255, 5))
        for _ in range(100):
            painter.drawPoint(random.randint(0, rect.width()), random.randint(0, rect.height()))

        # 3. 星星 (莫兰迪蓝 80%)
        for star in self.stars:
            color = QtGui.QColor("#a8d8ea")
            color.setAlpha(int(star.get('alpha', 255))) # 动画会控制alpha
            painter.setBrush(color)
            
            # 光晕
            if star['type'] == 'main':
                glow_color = QtGui.QColor("#a8d8ea")
                glow_color.setAlpha(76) # 30%
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawEllipse(QtCore.QPointF(star['x'], star['y']), star['size']*2, star['size']*2)
            
            painter.setPen(QtCore.Qt.NoPen)
            s = star['size']
            painter.drawEllipse(QtCore.QPointF(star['x'], star['y']), s/2, s/2)
            
        # 4. 流星 (莫兰迪蓝 60%)
        if self.shooting_star:
            p = self.shooting_star['progress']
            if p > 0.5:
                real_p = (p - 0.5) * 2
                if real_p < 0.5:
                    alpha = (real_p / 0.5) * 153 # 60% = 153
                else:
                    alpha = ((1.0 - real_p) / 0.5) * 153
                    
                pen = QtGui.QPen(QtGui.QColor("#a8d8ea"), 1)
                color = QtGui.QColor("#a8d8ea")
                color.setAlpha(int(alpha))
                pen.setColor(color)
                painter.setPen(pen)
                
                sx = self.shooting_star['start_x'] + (self.shooting_star['end_x'] - self.shooting_star['start_x']) * real_p
                sy = self.shooting_star['start_y'] + (self.shooting_star['end_y'] - self.shooting_star['start_y']) * real_p
                painter.drawLine(QtCore.QPointF(sx, sy), QtCore.QPointF(sx-3, sy-3))

        # 5. 边框 (莫兰迪蓝 30%)
        border_pen = QtGui.QPen(QtGui.QColor(168, 216, 234, 76), 2)
        painter.setPen(border_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 12, 12)
        
        # 6. 内发光 (微光晕)
        # 模拟 inset box-shadow: inset 0 0 20px rgba(168, 216, 234, 0.05)
        # 用渐变框模拟
        inner_glow = QtGui.QLinearGradient(0, 0, 0, rect.height())
        inner_glow.setColorAt(0, QtGui.QColor(168, 216, 234, 13)) # 5%
        inner_glow.setColorAt(1, QtGui.QColor(168, 216, 234, 5)) 
        
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(inner_glow)
        # 只绘制边缘内部一圈比较复杂，这里简化为覆盖一层淡的
        painter.drawRoundedRect(rect.adjusted(2,2,-2,-2), 10, 10)


class SimpleDailyReport(ReportEnvelopeContainer):
    clicked = Signal()

    def __init__(self):
        super().__init__(expanded_height=950)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.drag_start_pos = None
        self.is_timeline_active = False

        # 信封渐变改为日报专用配色
        self.toggle_button.set_gradient("#D4E0BB", "#E0E1AC")

        screen = None
        if hasattr(QtGui.QGuiApplication, "screenAt"):
            screen = QtGui.QGuiApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            target_height = min(1000, max(700, available.height() - 80))
            self.expanded_height = target_height
            self.resize(480, self.collapsed_height)
        else:
            self.resize(480, self.collapsed_height)
        self._center_on_screen()

        # 初始化新组件
        self.image_exporter = ImageExporter(self)
        self.timeline_view = TimelineView(self)
        self.feedback_system = FeedbackSystem(self)
        # self.motivational_footer = MotivationalFooter(self) # 移除未使用的组件以避免 ghost text bug
        self.enhanced_particle_effect = EnhancedParticleEffect(self)

        # 创建粒子覆盖层，确保粒子效果在最顶层
        self.particle_overlay = ParticleOverlay(self)

        # 连接信号
        self.image_exporter.exportCompleted.connect(self._on_export_success)
        self.image_exporter.exportFailed.connect(self._on_export_failed)
        self.timeline_view.closed.connect(self._on_timeline_closed)
        self.stateChanged.connect(self._on_collapse_state_changed)

        # 现代化卡片容器作为信封展开后的内容
        self.card_widget = StarryCardWidget()
        
        # 增强的阴影效果
        shadow = QtWidgets.QGraphicsDropShadowEffect(self.card_widget)
        shadow.setBlurRadius(DesignTokens.SHADOWS['xl']['blur'])
        shadow.setColor(QtGui.QColor(DesignTokens.SHADOWS['xl']['color']))
        shadow.setOffset(*DesignTokens.SHADOWS['xl']['offset'])
        self.card_widget.setGraphicsEffect(shadow)

        # 将卡片设置为 ReportEnvelopeContainer 的内容
        self.set_content(self.card_widget)

        # 内容布局
        content_layout = QtWidgets.QVBoxLayout(self.card_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 1. 现代化标题区
        title_box = QtWidgets.QWidget()
        title_box.setFixedHeight(120)
        tb_layout = QtWidgets.QVBoxLayout(title_box)
        tb_layout.setContentsMargins(30, 30, 30, 15)
        tb_layout.setSpacing(8)

        # 主标题 - 使用现代字体和渐变色
        lbl_t1 = QtWidgets.QLabel("今天又是努力的一天呢！")
        title_style = f"""
            QLabel {{
                color: #50795D;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 22px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }}
        """
        lbl_t1.setStyleSheet(title_style)

        # 副标题
        lbl_t2 = QtWidgets.QLabel("来看看你的进步足迹吧 ✨")
        subtitle_style = f"""
            QLabel {{
                color: #A05C3B;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
                font-weight: 400;
            }}
        """
        lbl_t2.setStyleSheet(subtitle_style)

        # 增强的标题动画
        self.title_opacity = QtWidgets.QGraphicsOpacityEffect(title_box)
        title_box.setGraphicsEffect(self.title_opacity)
        self.title_opacity.setOpacity(0)

        # 使用设计令牌的动画
        self.anim_title = QtCore.QPropertyAnimation(
            self.title_opacity, b"opacity")
        self.anim_title.setDuration(500)
        self.anim_title.setStartValue(0)
        self.anim_title.setEndValue(1)
        self.anim_title.setEasingCurve(DesignTokens.EASINGS['ease_out'])
        self.anim_title.start()

        tb_layout.addWidget(lbl_t1)
        tb_layout.addWidget(lbl_t2)
        content_layout.addWidget(title_box)

        # 2. 数据卡片列表
        self.cards_container = QtWidgets.QWidget()
        cc_layout = QtWidgets.QVBoxLayout(self.cards_container)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)

        # 现代化分隔线辅助函数 - 增加间距
        def add_line():
            # 创建更大的间距区域，无可见分隔线
            line_container = QtWidgets.QWidget()
            line_container.setFixedHeight(25)  # 增加间距
            line_container.setStyleSheet("background: transparent;")
            cc_layout.addWidget(line_container)

        # 卡片1
        self.c1 = Card1_Focus()
        cc_layout.addWidget(self.c1)
        add_line()

        # 文案框1
        self.msg1 = self.create_msg_box("比昨天多出<span style='color: #FFA500;'>30分钟</span>！进步看得见！", "#3498db")
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
        self.cards_pos = AnimatedValue(50.0)  # offset y
        self.cards_pos.valueChanged.connect(self.update_cards_pos)
        self.cards_pos.animate_to(0, 400, 100, QtCore.QEasingCurve.OutQuad)

        # 3. 现代化底部操作区
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(90)
        f_layout = QtWidgets.QHBoxLayout(footer)
        f_layout.setContentsMargins(30, 15, 30, 25)

        # 现代化按钮样式
        btn1 = QtWidgets.QPushButton("📊 查看时间轴")
        btn2 = QtWidgets.QPushButton("📤 导出图片")

        # 使用星空主题的按钮样式
        modern_btn_style = """
            QPushButton {
                color: #50795D;
                background: rgba(168, 216, 234, 0.15);
                border: 1px solid rgba(168, 216, 234, 0.4);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background: rgba(168, 216, 234, 0.25);
                color: #FFA500;
                border: 1px solid rgba(168, 216, 234, 0.6);
                box-shadow: 0 0 12px rgba(168, 216, 234, 0.3);
            }
            QPushButton:pressed {
                background: rgba(168, 216, 234, 0.35);
                color: #FFA500;
                border: 1px solid rgba(168, 216, 234, 0.8);
            }
        """

        # 连接按钮事件
        btn1.clicked.connect(self._show_timeline)
        btn2.clicked.connect(self._export_image)

        # 添加按钮悬停和点击反馈
        self._add_button_feedback(btn1)
        self._add_button_feedback(btn2)

        for btn in [btn1, btn2]:
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet(modern_btn_style)
            btn.setMinimumWidth(120)

        f_layout.addWidget(btn1)
        f_layout.addStretch()
        f_layout.addWidget(btn2)

        content_layout.addWidget(footer)

        # 移除励志文字区域，添加更多空白空间
        content_layout.addStretch()

        # 设置粒子覆盖层
        self.particle_overlay.set_particle_effect(
            self.enhanced_particle_effect)
        self.particle_overlay.show()

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
                background-color: transparent;
                border: none;
                padding: 12px 20px;
                color: #5E8E79;
                font-size: 16px;
                font-weight: 500;
                font-family: 'Segoe UI', 'Microsoft YaHei';
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

    def _on_timeline_closed(self):
        """时间轴关闭时的回调"""
        self.is_timeline_active = False
        self.setGraphicsEffect(None)
        
        # 强制立即刷新，确保虚化效果立即移除
        self.repaint()
        QtWidgets.QApplication.processEvents()
        
        # 重新激活自身，以便能够响应下一次的点击外部关闭
        self.activateWindow()

    def changeEvent(self, event):
        """处理窗口状态变化"""
        if event.type() == QtCore.QEvent.ActivationChange:
            # 如果失去焦点，且时间轴未激活，则关闭
            if not self.isActiveWindow() and not self.is_timeline_active:
                self.close()
        super().changeEvent(event)

    def _show_timeline(self):
        """显示时间轴视图"""
        self.is_timeline_active = True
        
        # 应用模糊效果
        blur = QtWidgets.QGraphicsBlurEffect(self)
        blur.setBlurRadius(10)
        self.setGraphicsEffect(blur)
        
        # 强制立即刷新，确保虚化效果在打开新窗口前呈现
        QtWidgets.QApplication.processEvents()

        self.timeline_view.show_timeline()

        # 触发金色粒子雨效果
        self.enhanced_particle_effect.create_golden_sparkle_shower(self.rect())
        self.particle_overlay.update_geometry()
        self.particle_overlay.raise_()
        self.particle_overlay.update()

    def _export_image(self):
        """导出图片"""
        self.image_exporter.export_to_file()

    def _on_export_success(self, file_path: str):
        """导出成功回调"""
        self.feedback_system.show_success_message("图片导出成功！", file_path)

        # 触发庆祝粒子效果
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.enhanced_particle_effect.create_success_sparkles(center)

    def _on_export_failed(self, error_message: str):
        """导出失败回调"""
        self.feedback_system.show_error_message(error_message)

    def _add_button_feedback(self, button: QtWidgets.QPushButton):
        """为按钮添加视觉反馈效果"""
        original_style = button.styleSheet()

        def on_press():
            # 点击时的视觉效果（移除不支持的transform）
            button.setStyleSheet(original_style + """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(52, 152, 219, 0.4),
                        stop:1 rgba(52, 152, 219, 0.2));
                }
            """)

            # 添加点击粒子效果
            button_rect = button.geometry()
            center = QtCore.QPoint(
                button_rect.center().x(),
                button_rect.center().y()
            )
            self.enhanced_particle_effect.create_celebration_burst(center, 8)

        def on_release():
            # 恢复原始样式
            button.setStyleSheet(original_style)

        button.pressed.connect(on_press)
        button.released.connect(on_release)

    def enterEvent(self, event):
        """鼠标进入窗口事件"""
        super().enterEvent(event)
        # 移除蓝色边框效果

    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        super().leaveEvent(event)
        # 移除发光效果

    def paintEvent(self, event):
        """重写paintEvent - 粒子效果现在由覆盖层处理"""
        # 绘制正常的UI内容
        super().paintEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and hasattr(self, 'drag_pos'):
            if hasattr(event, 'globalPosition'):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            self.move(pos - self.drag_pos)
            event.accept()

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 更新粒子覆盖层的几何位置
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.update_geometry()

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.raise_()
            self.particle_overlay.update_geometry()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = None
        if hasattr(QtGui.QGuiApplication, "screenAt"):
            screen = QtGui.QGuiApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            geo = self.frameGeometry()
            geo.moveCenter(available.center())
            self.move(geo.topLeft())

    def _create_compact_content(self):
        """创建折叠模式的紧凑内容"""
        compact_widget = QtWidgets.QWidget()
        compact_widget.setObjectName("CompactWidget")

        # 使用暗色主题的简洁样式
        modern_style = f"""
            QWidget#CompactWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {DesignTokens.COLORS['surface']},
                    stop:1 {DesignTokens.COLORS['background']});
                border-radius: 16px;
                border: 1px solid {DesignTokens.COLORS['border']};
            }}
        """
        compact_widget.setStyleSheet(modern_style)

        # 添加更柔和的阴影效果
        shadow = QtWidgets.QGraphicsDropShadowEffect(compact_widget)
        shadow.setBlurRadius(DesignTokens.SHADOWS['lg']['blur'])
        shadow.setColor(QtGui.QColor(DesignTokens.SHADOWS['lg']['color']))
        shadow.setOffset(*DesignTokens.SHADOWS['lg']['offset'])
        compact_widget.setGraphicsEffect(shadow)

        layout = QtWidgets.QVBoxLayout(compact_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 紧凑标题
        title_label = QtWidgets.QLabel("📊 今日专注概览")
        title_style = f"""
            QLabel {{
                color: {DesignTokens.COLORS['text_primary']};
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 16px;
                font-weight: 600;
            }}
        """
        title_label.setStyleSheet(title_style)
        layout.addWidget(title_label)

        # 关键数据摘要
        summary_layout = QtWidgets.QHBoxLayout()

        # 专注时长
        focus_widget = QtWidgets.QWidget()
        focus_layout = QtWidgets.QVBoxLayout(focus_widget)
        focus_layout.setContentsMargins(0, 0, 0, 0)

        focus_value = QtWidgets.QLabel("4.5小时")
        focus_value.setStyleSheet(f"""
            QLabel {{
                color: {DesignTokens.COLORS['accent']};
                font-size: 18px;
                font-weight: bold;
            }}
        """)

        focus_desc = QtWidgets.QLabel("专注时长")
        focus_desc.setStyleSheet(f"""
            QLabel {{
                color: #A05C3B;
                font-size: 10px;
            }}
        """)

        focus_layout.addWidget(focus_value)
        focus_layout.addWidget(focus_desc)

        # 分心次数
        distract_widget = QtWidgets.QWidget()
        distract_layout = QtWidgets.QVBoxLayout(distract_widget)
        distract_layout.setContentsMargins(0, 0, 0, 0)

        distract_value = QtWidgets.QLabel("7次")
        distract_value.setStyleSheet(f"""
            QLabel {{
                color: #6A4A3F;
                font-size: 18px;
                font-weight: bold;
            }}
        """)

        distract_desc = QtWidgets.QLabel("分心次数")
        distract_desc.setStyleSheet(f"""
            QLabel {{
                color: #A05C3B;
                font-size: 10px;
            }}
        """)

        distract_layout.addWidget(distract_value)
        distract_layout.addWidget(distract_desc)

        summary_layout.addWidget(focus_widget)
        summary_layout.addStretch()
        summary_layout.addWidget(distract_widget)

        layout.addLayout(summary_layout)

        # 紧凑按钮区域
        button_layout = QtWidgets.QHBoxLayout()

        timeline_btn = QtWidgets.QPushButton("📊 时间轴")
        export_btn = QtWidgets.QPushButton("📤 导出")

        compact_btn_style = f"""
            QPushButton {{
                color: {DesignTokens.COLORS['text_primary']};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {DesignTokens.COLORS['surface']},
                    stop:1 {DesignTokens.COLORS['background']});
                border: 1px solid {DesignTokens.COLORS['primary']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {DesignTokens.COLORS['primary']},
                    stop:1 {DesignTokens.COLORS['primary_dark']});
                border: 1px solid {DesignTokens.COLORS['primary_light']};
                color: {DesignTokens.COLORS['background']};
            }}
        """

        timeline_btn.setStyleSheet(compact_btn_style)
        export_btn.setStyleSheet(compact_btn_style)

        # 连接按钮事件
        timeline_btn.clicked.connect(self._show_timeline)
        export_btn.clicked.connect(self._export_image)

        button_layout.addWidget(timeline_btn)
        button_layout.addStretch()
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)

        return compact_widget

    def _on_collapse_state_changed(self, is_expanded: bool):
        """折叠状态改变回调"""
        if is_expanded:
            # 展开时触发金色粒子雨效果 - 延迟触发以配合动画
            def trigger_particles():
                print("展开触发金色粒子雨效果")  # 调试信息
                self.enhanced_particle_effect.create_golden_sparkle_shower(
                    self.rect())
                self.particle_overlay.update_geometry()
                self.particle_overlay.raise_()
                self.particle_overlay.update()

            QtCore.QTimer.singleShot(300, trigger_particles)
            QtCore.QTimer.singleShot(320, self._center_on_screen)


def show_simple_daily():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.AA_EnableHighDpiScaling, True)

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
