import sys
import math
from PySide6 import QtCore, QtGui, QtWidgets

# 导入视觉增强组件
try:
    from ..visual_enhancements.dark_theme_manager import DarkThemeManager
    from ..visual_enhancements.startup_particle_system import StartupParticleSystem
    from ..visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
    from ..visual_enhancements.visual_effects_manager import VisualEffectsManager
    from ..visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
    from ..visual_enhancements.suggestion_dialog import SuggestionDialog
    from ..visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from visual_enhancements.dark_theme_manager import DarkThemeManager
    from visual_enhancements.startup_particle_system import StartupParticleSystem
    from visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
    from visual_enhancements.visual_effects_manager import VisualEffectsManager
    from visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
    from visual_enhancements.suggestion_dialog import SuggestionDialog
    from visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager

# --- 辅助类：带动画的数值/属性 ---


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

# --- 右栏：洞察卡片 ---


class InsightCard(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self, title, subtitle, desc, detail_hint="→ 点击查看详细建议"):
        super().__init__()
        self.setFixedSize(200, 140)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 初始化视觉增强组件
        self.theme_manager = DarkThemeManager.get_instance()
        self.animation_engine = PrecisionAnimationEngine(self)
        self.effects_manager = VisualEffectsManager(self)
        self.feedback_system = InteractionFeedbackSystem(self)

        # 初始化交互管理器
        self.interaction_manager = InsightCardInteractionManager(self)

        # 属性动画变量
        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        self.title = title
        self.subtitle = subtitle
        self.desc = desc
        self.detail_hint = detail_hint

        # 应用暗色主题和视觉效果
        self._setup_visual_enhancements()

        # 设置卡片交互
        self._setup_card_interaction()

    def _setup_visual_enhancements(self):
        """设置视觉增强效果"""
        # 应用卡片阴影效果
        self.effects_manager.apply_card_shadow(
            self, blur_radius=20, offset=(0, 6))

        # 设置交互反馈
        self.feedback_system.setup_hover_feedback(self, scale_factor=1.03)
        self.feedback_system.setup_click_feedback(self, with_particles=True)

    def _setup_card_interaction(self):
        """设置卡片交互功能"""
        # 使用交互管理器设置卡片交互
        success = self.interaction_manager.setup_card_interaction(
            self, self.title)

        if success:
            print(f"卡片交互设置成功: {self.title}")

            # 连接交互管理器的信号
            self.interaction_manager.cardClicked.connect(
                lambda title: print(f"交互管理器报告卡片点击: {title}")
            )
            self.interaction_manager.dialogRequested.connect(
                lambda suggestion_type: print(f"请求显示建议类型: {suggestion_type}")
            )
            self.interaction_manager.interactionError.connect(
                lambda error_type, message: print(
                    f"交互错误 [{error_type}]: {message}")
            )
        else:
            print(f"卡片交互设置失败: {self.title}")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        progress = self.hover_progress.value

        # 动态布局调整
        offset_y = -5 * progress  # 悬停上浮 5px

        # 暗色主题背景
        rect = QtCore.QRectF(
            5, 5 + offset_y, self.width()-10, self.height()-10)

        # 暗色卡片背景
        bg_color = self.theme_manager.get_color('background_card')
        p.setBrush(bg_color)

        # 边框 (悬停时使用绿色发光)
        if progress > 0.1:
            border_color = self.theme_manager.get_color('accent_green')
            border_color.setAlphaF(0.6 * progress)
            p.setPen(QtGui.QPen(border_color, 2 + progress))
        else:
            border_color = self.theme_manager.get_color('border_color')
            p.setPen(QtGui.QPen(border_color, 1))

        p.drawRoundedRect(rect, 12, 12)

        # 暗色主题文字绘制
        # 标题 - 使用主要文字颜色
        p.setPen(self.theme_manager.get_color('text_primary'))
        font = self.theme_manager.get_font('heading')
        font.setPixelSize(11)
        p.setFont(font)
        p.drawText(rect.adjusted(15, 15, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.title)

        # 副标题 - 使用强调绿色
        font = self.theme_manager.get_font('primary')
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(self.theme_manager.get_color('accent_green'))
        p.drawText(rect.adjusted(15, 40, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.subtitle)

        # 描述文字 - 使用次要文字颜色
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(self.theme_manager.get_color('text_secondary'))
        rect_desc = rect.adjusted(15, 65, -15, -30)
        p.drawText(rect_desc, QtCore.Qt.AlignLeft |
                   QtCore.Qt.TextWordWrap, self.desc)

        # 底部提示 - 悬停时显示绿色发光效果
        if progress > 0.05:
            p.setOpacity(progress)
            font.setPixelSize(10)
            p.setFont(font)
            p.setPen(self.theme_manager.get_color('accent_green_light'))
            p.drawText(rect.adjusted(15, 0, -15, -10), QtCore.Qt.AlignLeft |
                       QtCore.Qt.AlignBottom, self.detail_hint)
            p.setOpacity(1.0)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        print(f"InsightCard mousePressEvent 被触发: {self.title}")

        # 防止重复处理点击事件
        if hasattr(self, '_processing_click') and self._processing_click:
            return

        self._processing_click = True

        # 触发点击动画
        anim = self.interaction_manager.trigger_click_animation(self)

        if anim:
            # 动画完成后处理卡片点击
            geo = self.geometry()
            anim.finished.connect(lambda: self.setGeometry(geo))  # 恢复几何形状
            anim.finished.connect(lambda: self._handle_click_after_animation())
        else:
            # 如果动画创建失败，直接处理点击
            self._handle_click_after_animation()

    def _handle_click_after_animation(self):
        """动画完成后处理点击"""
        try:
            # 处理卡片点击，传递卡片组件以便触发粒子效果
            success = self.interaction_manager.handle_card_click(
                self.title, self)

            # 发出点击信号（只在成功时发出）
            if success:
                self.clicked.emit()
        finally:
            # 重置处理标志
            self._processing_click = False

    def show_suggestion_dialog(self):
        """显示建议弹窗 - 保留原方法作为备用"""
        print(f"[备用方法] 点击了卡片: {self.title}")

        # 使用交互管理器处理
        success = self.interaction_manager.handle_card_click(self.title)

        if not success:
            print(f"交互管理器处理失败，尝试直接创建弹窗")
            try:
                # 备用方案：直接创建弹窗
                self.dialog = SuggestionDialog(self.title, self.window())
                print(f"备用弹窗创建成功，建议数据: {bool(self.dialog.suggestion_data)}")
                self.dialog.show_with_animation()
                print("备用弹窗显示完成")
            except Exception as e:
                print(f"备用弹窗显示失败: {e}")
                import traceback
                traceback.print_exc()

# --- 中栏：对比图 ---


class BarItem:
    def __init__(self, label, value, color, delay, is_current=False):
        self.label = label
        self.target_value = value
        self.current_height = AnimatedValue(0.0)
        self.color = QtGui.QColor(color)
        self.delay = delay
        self.is_current = is_current


class ComparisonChart(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 400)

        # 初始化视觉增强组件
        self.theme_manager = DarkThemeManager.get_instance()
        self.animation_engine = PrecisionAnimationEngine(self)

        # 使用暗色主题的数据定义
        self.bars = [
            BarItem("三周前", 4.5, self.theme_manager.COLORS['accent_blue'], 800),
            BarItem(
                "两周前", 3.8, self.theme_manager.COLORS['accent_yellow'], 600),
            BarItem(
                "上周", 4.1, self.theme_manager.COLORS['accent_green_dark'], 400),
            BarItem(
                "本周", 5.2, self.theme_manager.COLORS['accent_green'], 200, is_current=True)
        ]

        self.max_val = 6.0

        # 启动动画
        for bar in self.bars:
            bar.current_height.valueChanged.connect(self.update)
            # 0 -> target_value
            bar.current_height.animate_to(
                bar.target_value, 800, bar.delay, QtCore.QEasingCurve.OutBack)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        padding_left = 60
        padding_bottom = 40
        padding_top = 60
        graph_w = w - padding_left - 20
        graph_h = h - padding_bottom - padding_top

        # 1. 绘制坐标轴和网格线 - 暗色主题
        p.setPen(self.theme_manager.get_color('border_color'))
        font = self.theme_manager.get_font('primary')
        p.setFont(font)

        grid_count = 4
        for i in range(grid_count + 1):
            val = self.max_val * i / grid_count
            y = padding_top + graph_h - (val / self.max_val * graph_h)

            # 网格线 - 暗色主题
            if i > 0:
                grid_color = self.theme_manager.get_color('separator_color')
                p.setPen(QtGui.QPen(grid_color, 1, QtCore.Qt.DashLine))
                p.drawLine(int(padding_left), int(y), int(w - 20), int(y))

            # Y轴刻度 - 使用次要文字颜色
            p.setPen(self.theme_manager.get_color('text_secondary'))
            p.drawText(QtCore.QRect(0, int(y - 10), padding_left - 10, 20),
                       QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, f"{val:.1f}h")

        # 2. 绘制柱子
        bar_width = graph_w / len(self.bars) * 0.6
        spacing = graph_w / len(self.bars)

        for i, bar in enumerate(self.bars):
            cx = padding_left + spacing * i + spacing / 2
            val = bar.current_height.value
            bar_h = (val / self.max_val) * graph_h

            # 柱子矩形 (底部对齐)
            rect = QtCore.QRectF(
                cx - bar_width/2, padding_top + graph_h - bar_h, bar_width, bar_h)

            if bar_h > 0:
                # 渐变填充
                grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
                c1 = bar.color
                c2 = bar.color.darker(150)
                grad.setColorAt(0, c1)
                grad.setColorAt(1, c2)
                p.setBrush(grad)
                p.setPen(QtCore.Qt.NoPen)
                p.drawRoundedRect(rect, 4, 4)

                # 顶部高光条
                highlight_rect = QtCore.QRectF(
                    rect.left(), rect.top(), rect.width(), 2)
                p.setBrush(QtGui.QColor(255, 255, 255, 180))
                p.drawRect(highlight_rect)

            # X轴标签 - 暗色主题
            p.setPen(self.theme_manager.get_color('text_secondary'))
            p.drawText(QtCore.QRectF(cx - spacing/2, h - padding_bottom + 5, spacing, 30),
                       QtCore.Qt.AlignCenter, bar.label)

            # 数值标签 (动画完成后显示，这里简化为高度接近目标时显示)
            if val > bar.target_value * 0.95:
                p.setPen(bar.color)
                p.drawText(QtCore.QRectF(cx - spacing/2, rect.top() - 25, spacing, 20),
                           QtCore.Qt.AlignCenter, f"{bar.target_value}h")

                # 皇冠图标 (本周) - 使用主题黄色
                if bar.is_current:
                    p.setPen(self.theme_manager.get_color('accent_yellow'))
                    font_icon = QtGui.QFont("Segoe UI Emoji", 12)
                    p.setFont(font_icon)
                    p.drawText(QtCore.QRectF(cx - spacing/2, rect.top() - 45, spacing, 20),
                               QtCore.Qt.AlignCenter, "👑")
                    p.setFont(font)  # 还原字体

# --- 左栏：成就墙 ---


class DayIcon(QtWidgets.QWidget):
    def __init__(self, day_name, date_str, hours, level, icon_type):
        super().__init__()
        self.setFixedSize(70, 100)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.day_name = day_name
        self.date_str = date_str
        self.hours = hours
        self.level = level
        self.icon_type = icon_type  # 'sun', 'star', 'cloud', 'moon'

        # 初始化视觉增强组件
        self.theme_manager = DarkThemeManager.get_instance()
        self.feedback_system = InteractionFeedbackSystem(self)

        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        # 设置交互反馈
        self.feedback_system.setup_hover_feedback(self, scale_factor=1.08)
        self.feedback_system.setup_click_feedback(self, with_particles=True)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        prog = self.hover_progress.value

        # 1. 绘制背景光晕 (Hover) - 暗色主题绿色发光
        if prog > 0.01:
            center = QtCore.QPointF(self.width()/2, 40)
            radius = 35 + 5 * prog
            grad = QtGui.QRadialGradient(center, radius)
            glow_color = self.theme_manager.get_color('accent_green')
            glow_color.setAlphaF(0.3 * prog)
            grad.setColorAt(0, glow_color)
            glow_color.setAlphaF(0)
            grad.setColorAt(1, glow_color)
            p.setBrush(grad)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(center, radius, radius)

        # 2. 绘制图标
        icon_size = 40 + 4 * prog  # 放大
        icon_rect = QtCore.QRectF(
            (self.width()-icon_size)/2, 40 - icon_size/2, icon_size, icon_size)

        self.draw_icon_shape(p, icon_rect, self.icon_type)

        # 3. 文字信息 - 暗色主题
        p.setPen(self.theme_manager.get_color('text_primary'))
        font = self.theme_manager.get_font('primary')
        font.setPixelSize(9)
        p.setFont(font)

        # 周几
        p.drawText(QtCore.QRect(0, 0, self.width(), 20),
                   QtCore.Qt.AlignCenter, self.day_name)

        # 日期 (在图标下方)
        p.setPen(self.theme_manager.get_color('text_secondary'))
        font.setPixelSize(8)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 65, self.width(), 15),
                   QtCore.Qt.AlignCenter, self.date_str)

        # 时长 - 使用强调绿色
        p.setPen(self.theme_manager.get_color('accent_green'))
        font.setPixelSize(9)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 80, self.width(), 15),
                   QtCore.Qt.AlignCenter, f"{self.hours}h")

    def draw_icon_shape(self, p, rect, type):
        if type == 'sun':
            p.setBrush(QtGui.QColor("#F1C40F"))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(4, 4, -4, -4))
            # 光芒 (简化)
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width()/2
            for i in range(8):
                angle = i * 45
                rad = math.radians(angle)
                ox = cx + math.cos(rad) * (r + 2)
                oy = cy + math.sin(rad) * (r + 2)
                p.setPen(QtGui.QPen(QtGui.QColor("#F39C12"), 2))
                p.drawLine(QtCore.QPointF(cx + math.cos(rad)*r, cy + math.sin(rad)*r),
                           QtCore.QPointF(ox, oy))

        elif type == 'star':
            p.setBrush(QtGui.QColor("#BDC3C7"))  # 银色
            p.setPen(QtCore.Qt.NoPen)
            # 简单的菱形模拟星星
            path = QtGui.QPainterPath()
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width()/2
            path.moveTo(cx, cy - r)
            path.lineTo(cx + r*0.3, cy - r*0.3)
            path.lineTo(cx + r, cy)
            path.lineTo(cx + r*0.3, cy + r*0.3)
            path.lineTo(cx, cy + r)
            path.lineTo(cx - r*0.3, cy + r*0.3)
            path.lineTo(cx - r, cy)
            path.lineTo(cx - r*0.3, cy - r*0.3)
            path.closeSubpath()
            p.drawPath(path)

        elif type == 'cloud':
            p.setBrush(QtGui.QColor("#95A5A6"))  # 灰色
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(2, 6, -2, -6))

        elif type == 'moon':
            p.setBrush(QtGui.QColor("#2C3E50"))  # 深蓝
            p.setPen(QtCore.Qt.NoPen)
            path = QtGui.QPainterPath()
            path.addEllipse(rect)
            cut = QtGui.QPainterPath()
            cut.addEllipse(rect.translated(
                rect.width()*0.3, -rect.height()*0.1))
            path = path.subtracted(cut)
            p.drawPath(path)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 300)
        # 这里可以实现弹出 tooltip 逻辑，简化起见，我们打印一下
        print(f"Hover: {self.day_name}")

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 300)


class AchievementWall(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)

        layout = QtWidgets.QGridLayout(self)
        layout.setSpacing(5)

        # 数据
        data = [
            ("周一", "12/8", 4.2, "专注", "sun"),
            ("周二", "12/9", 6.1, "巅峰", "sun"),
            ("周三", "12/10", 5.8, "优秀", "sun"),
            ("周四", "12/11", 2.5, "放松", "cloud"),
            ("周五", "12/12", 5.2, "良好", "sun"),
            ("周六", "12/13", 3.0, "休息", "star"),
            ("周日", "12/14", 4.5, "恢复", "moon"),
        ]

        for i, (day, date, h, lvl, icon) in enumerate(data):
            item = DayIcon(day, date, h, lvl, icon)
            row = i // 4
            col = i % 4
            layout.addWidget(item, row, col)

# --- 主仪表盘 ---


class WeeklyDashboard(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.resize(900, 600)
        self.drag_start_pos = None

        # 初始化视觉增强组件
        self.theme_manager = DarkThemeManager.get_instance()
        self.animation_engine = PrecisionAnimationEngine(self)
        self.effects_manager = VisualEffectsManager(self)

        # 圆角窗口设置
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 主布局
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(30, 40, 30, 40)
        self.main_layout.setSpacing(20)

        # 左栏
        self.left_panel = AchievementWall()
        self.left_anim_opacity = QtWidgets.QGraphicsOpacityEffect(
            self.left_panel)
        self.left_panel.setGraphicsEffect(self.left_anim_opacity)
        self.left_anim_opacity.setOpacity(0)

        # 中栏
        self.mid_panel = ComparisonChart()
        self.mid_anim_opacity = QtWidgets.QGraphicsOpacityEffect(
            self.mid_panel)
        self.mid_panel.setGraphicsEffect(self.mid_anim_opacity)
        self.mid_anim_opacity.setOpacity(0)

        # 右栏
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setFixedWidth(220)
        r_layout = QtWidgets.QVBoxLayout(self.right_panel)
        r_layout.addWidget(InsightCard(
            "💡 效率高峰期", "上午9-11点", "抓住黄金时段，学霸体质get！"))
        r_layout.addWidget(InsightCard("⚠️ 易分心时段", "下午3点后", "不妨安排轻松任务，灵活调整~"))
        r_layout.addWidget(InsightCard("📈 成长趋势", "本周提升15%", "稳步上升，势头强劲！"))
        r_layout.addStretch()

        self.right_anim_opacity = QtWidgets.QGraphicsOpacityEffect(
            self.right_panel)
        self.right_panel.setGraphicsEffect(self.right_anim_opacity)
        self.right_anim_opacity.setOpacity(0)

        # 添加到主布局
        self.main_layout.addWidget(self.left_panel)

        # 分隔线 1 - 暗色主题
        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.VLine)
        self.effects_manager.apply_separator_glow(line1)
        self.main_layout.addWidget(line1)

        self.main_layout.addWidget(self.mid_panel)

        # 分隔线 2 - 暗色主题
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.VLine)
        self.effects_manager.apply_separator_glow(line2)
        self.main_layout.addWidget(line2)

        self.main_layout.addWidget(self.right_panel)

        # 创建启动粒子系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.resize(self.size())

        # 启动入场动画和粒子效果
        self.start_entrance_animation()
        QtCore.QTimer.singleShot(800, self.trigger_startup_particles)

    def paintEvent(self, event):
        # 绘制暗色主题背景
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # 暗色主题背景
        bg_color = self.theme_manager.get_color('background_primary')
        p.setBrush(bg_color)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(self.rect(), 40, 40)

        # 添加微妙的边框
        border_color = self.theme_manager.get_color('border_color')
        p.setPen(QtGui.QPen(border_color, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 40, 40)

    def start_entrance_animation(self):
        # 依次淡入
        # 左栏 0ms
        self.anim1 = QtCore.QPropertyAnimation(
            self.left_anim_opacity, b"opacity")
        self.anim1.setDuration(600)
        self.anim1.setStartValue(0)
        self.anim1.setEndValue(1)
        self.anim1.start()

        # 中栏 200ms
        self.anim2 = QtCore.QPropertyAnimation(
            self.mid_anim_opacity, b"opacity")
        self.anim2.setDuration(600)
        self.anim2.setStartValue(0)
        self.anim2.setEndValue(1)
        QtCore.QTimer.singleShot(200, self.anim2.start)

        # 右栏 400ms
        self.anim3 = QtCore.QPropertyAnimation(
            self.right_anim_opacity, b"opacity")
        self.anim3.setDuration(600)
        self.anim3.setStartValue(0)
        self.anim3.setEndValue(1)
        QtCore.QTimer.singleShot(400, self.anim3.start)

    def trigger_startup_particles(self):
        """触发启动粒子庆祝效果"""
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.particle_system.trigger_startup_effect(center)

    def resizeEvent(self, event):
        """窗口大小改变时调整粒子系统"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_system'):
            self.particle_system.resize(self.size())

    def mousePressEvent(self, event):
        # 允许拖动窗口
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_start_pos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos is not None and event.button() == QtCore.Qt.LeftButton:
            drag_distance = (event.globalPos() -
                             self.drag_start_pos).manhattanLength()
            if drag_distance < QtWidgets.QApplication.startDragDistance():
                self.clicked.emit()
            self.drag_start_pos = None
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()


def show_weekly_report():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    # 启用高 DPI
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.AA_EnableHighDpiScaling, True)

    window = WeeklyDashboard()
    window.show()

    if not QtWidgets.QApplication.instance():
        sys.exit(app.exec())
    else:
        app.exec()


if __name__ == "__main__":
    show_weekly_report()
