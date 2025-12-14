import sys
import math
import random
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty

# 导入视觉增强组件
try:
    from ui.component.visual_enhancements.startup_particle_system import StartupParticleSystem
    from ui.component.visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
    from ui.component.visual_enhancements.visual_effects_manager import VisualEffectsManager
    from ui.component.visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
    from ui.component.visual_enhancements.suggestion_dialog import SuggestionDialog
    from ui.component.visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager
except ImportError:
    # 如果失败，可能是直接运行此文件，需要手动添加项目根目录到 path
    import sys
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        
    try:
        from ui.component.visual_enhancements.startup_particle_system import StartupParticleSystem
        from ui.component.visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
        from ui.component.visual_enhancements.visual_effects_manager import VisualEffectsManager
        from ui.component.visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
        from ui.component.visual_enhancements.suggestion_dialog import SuggestionDialog
        from ui.component.visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager
    except ImportError:
        try:
            from ..visual_enhancements.startup_particle_system import StartupParticleSystem
            from ..visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
            from ..visual_enhancements.visual_effects_manager import VisualEffectsManager
            from ..visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
            from ..visual_enhancements.suggestion_dialog import SuggestionDialog
            from ..visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager
        except ImportError:
            # Fallback for direct execution if path setup worked
            from visual_enhancements.startup_particle_system import StartupParticleSystem
            from visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
            from visual_enhancements.visual_effects_manager import VisualEffectsManager
            from visual_enhancements.interaction_feedback_system import InteractionFeedbackSystem
            from visual_enhancements.suggestion_dialog import SuggestionDialog
            from visual_enhancements.insight_card_interaction_manager import InsightCardInteractionManager

# 导入统一主题
try:
    from ui.component.report.report_theme import theme as MorandiTheme
except ImportError:
    try:
        from .report_theme import theme as MorandiTheme
    except ImportError:
        from report_theme import theme as MorandiTheme

# --- 辅助类：带动画的数值/属性 ---


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

# --- 右栏：洞察卡片 ---


class InsightCard(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self, title, subtitle, desc, detail_hint="→ 点击查看详细建议"):
        super().__init__()
        self.setFixedSize(200, 140)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 初始化视觉增强组件
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

        # 应用视觉效果
        self._setup_visual_enhancements()

        # 设置卡片交互
        self._setup_card_interaction()

    def _setup_visual_enhancements(self):
        """设置视觉增强效果"""
        # 应用卡片阴影效果
        # 使用莫兰迪阴影：外阴影
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QtGui.QColor(0, 0, 0, 20)) # 0.08 alpha
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        # 设置交互反馈 - 移除 setup_hover_feedback 以避免与 paintEvent 冲突
        # self.feedback_system.setup_hover_feedback(self, scale_factor=1.03)
        self.feedback_system.setup_click_feedback(self, with_particles=True)

    def _setup_card_interaction(self):
        """设置卡片交互功能"""
        # 使用交互管理器设置卡片交互
        success = self.interaction_manager.setup_card_interaction(
            self, self.title)

        if success:
            # 连接交互管理器的信号
            self.interaction_manager.cardClicked.connect(
                lambda title: print(f"交互管理器报告卡片点击: {title}")
            )

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        progress = self.hover_progress.value
        
        # 手动实现缩放效果 (替代 InteractionFeedbackSystem)
        if progress > 0:
            scale = 1.0 + 0.03 * progress
            cx, cy = self.width() / 2, self.height() / 2
            p.translate(cx, cy)
            p.scale(scale, scale)
            p.translate(-cx, -cy)

        # 动态布局调整
        offset_y = -5 * progress  # 悬停上浮 5px

        # 背景区域
        rect = QtCore.QRectF(
            5, 5 + offset_y, self.width()-10, self.height()-10)

        # 莫兰迪背景 (透明度很低，依靠主窗口背景，这里加一点点叠加)
        bg_color = QtGui.QColor(168, 216, 234, 15) # 极淡的背景
        p.setBrush(bg_color)

        # 边框 (悬停时金色发光)
        if progress > 0.1:
            border_color = QtGui.QColor("#ffd700")
            border_color.setAlphaF(0.6 * progress)
            p.setPen(QtGui.QPen(border_color, 2 + progress))
            
            # 悬停光晕
            glow_rect = rect.adjusted(-2, -2, 2, 2)
            glow_color = QtGui.QColor(168, 216, 234, 76)
            p.setBrush(glow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(glow_rect, 12, 12)
            p.setBrush(bg_color) # 恢复背景
            
        else:
            border_color = MorandiTheme.COLOR_BORDER
            p.setPen(QtGui.QPen(border_color, 1))

        p.drawRoundedRect(rect, 12, 12)

        # 文字绘制
        # 标题 - 莫兰迪蓝 90%
        p.setPen(MorandiTheme.COLOR_TEXT_TITLE)
        font = QtGui.QFont("Noto Sans SC", 11, QtGui.QFont.Bold)
        p.setFont(font)
        p.drawText(rect.adjusted(15, 15, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.title)

        # 星星图标 (如果在标题旁) - 这里直接绘制在标题右侧
        if "✨" not in self.title: # 简单判断，如果需要额外绘制
            # 这里假设标题文本不包含星星，手动绘制一个金色星星
            # 但用户说 "保持原✨位置(标题旁)"，InsightCard里原代码没画星星
            # 我们假设它包含在 title 字符串里，或者我们可以画一个
            pass

        # 副标题 (数据值) - 金色 100% + 发光
        font_sub = QtGui.QFont("Noto Sans SC", 12)
        p.setFont(font_sub)
        p.setPen(MorandiTheme.COLOR_TEXT_VALUE)
        
        # 绘制文字阴影 (模拟发光)
        p.save()
        p.translate(0, 0)
        shadow_color = QtGui.QColor(255, 215, 0, 76) # 0.3 alpha
        # 简单模拟glow: 多次绘制微小偏移? 还是直接用Pen color?
        # Qt text shadow is hard without GraphicsEffect. 
        # We can just draw semi-transparent text underneath?
        # Or just trust the color.
        p.restore()
        
        p.drawText(rect.adjusted(15, 40, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.subtitle)

        # 描述文字 - 莫兰迪蓝 80%
        font_desc = QtGui.QFont("Noto Sans SC", 11)
        p.setFont(font_desc)
        p.setPen(MorandiTheme.COLOR_TEXT_DESC)
        rect_desc = rect.adjusted(15, 65, -15, -30)
        p.drawText(rect_desc, QtCore.Qt.AlignLeft |
                   QtCore.Qt.TextWordWrap, self.desc)

        # 底部提示 - 悬停时显示金色
        if progress > 0.05:
            p.setOpacity(progress)
            font_hint = QtGui.QFont("Noto Sans SC", 10)
            p.setFont(font_hint)
            p.setPen(QtGui.QColor("#ffd700"))
            p.drawText(rect.adjusted(15, 0, -15, -10), QtCore.Qt.AlignLeft |
                       QtCore.Qt.AlignBottom, self.detail_hint)
            p.setOpacity(1.0)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)

    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if hasattr(self, '_processing_click') and self._processing_click:
            return

        self._processing_click = True
        anim = self.interaction_manager.trigger_click_animation(self)

        if anim:
            geo = self.geometry()
            anim.finished.connect(lambda: self.setGeometry(geo))
            anim.finished.connect(lambda: self._handle_click_after_animation())
        else:
            self._handle_click_after_animation()

    def _handle_click_after_animation(self):
        """动画完成后处理点击"""
        try:
            success = self.interaction_manager.handle_card_click(
                self.title, self)
            if success:
                self.clicked.emit()
        finally:
            self._processing_click = False

# --- 中栏：对比图 ---


class BarItem:
    def __init__(self, label, value, delay, is_current=False):
        self.label = label
        self.target_value = value
        self.current_height = AnimatedValue(0.0)
        self.delay = delay
        self.is_current = is_current


class ComparisonChart(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 400)

        # 初始化视觉增强组件
        self.animation_engine = PrecisionAnimationEngine(self)

        self.bars = [
            BarItem("三周前", 4.5, 800),
            BarItem("两周前", 3.8, 600),
            BarItem("上周", 4.1, 400),
            BarItem("本周", 5.2, 200, is_current=True)
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

        # 1. 绘制坐标轴和网格线
        p.setPen(MorandiTheme.COLOR_BORDER)
        font = QtGui.QFont("Noto Sans SC", 9)
        p.setFont(font)

        grid_count = 4
        for i in range(grid_count + 1):
            val = self.max_val * i / grid_count
            y = padding_top + graph_h - (val / self.max_val * graph_h)

            # 网格线 - 极淡蓝
            if i > 0:
                p.setPen(QtGui.QPen(MorandiTheme.COLOR_GRID, 1, QtCore.Qt.DashLine))
                p.drawLine(int(padding_left), int(y), int(w - 20), int(y))

            # Y轴刻度 - 莫兰迪蓝 70%
            p.setPen(MorandiTheme.COLOR_TEXT_DATE)
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
                # 填充: 金色 60%
                p.setBrush(MorandiTheme.COLOR_CHART_BAR)
                # 边框: 莫兰迪蓝 40%
                p.setPen(QtGui.QPen(MorandiTheme.COLOR_CHART_BORDER, 1))
                p.drawRoundedRect(rect, 4, 4)

            # X轴标签 - 莫兰迪蓝 70%
            p.setPen(MorandiTheme.COLOR_TEXT_DATE)
            p.drawText(QtCore.QRectF(cx - spacing/2, h - padding_bottom + 5, spacing, 30),
                       QtCore.Qt.AlignCenter, bar.label)

            # 数值标签 (金色)
            if val > bar.target_value * 0.95:
                p.setPen(MorandiTheme.COLOR_TEXT_VALUE)
                font_val = QtGui.QFont("Noto Sans SC", 10, QtGui.QFont.Bold)
                p.setFont(font_val)
                p.drawText(QtCore.QRectF(cx - spacing/2, rect.top() - 25, spacing, 20),
                           QtCore.Qt.AlignCenter, f"{bar.target_value}h")
                p.setFont(font) # 还原

                # 皇冠图标 (本周) - 金色
                if bar.is_current:
                    p.setPen(QtGui.QColor("#ffd700"))
                    font_icon = QtGui.QFont("Segoe UI Emoji", 12)
                    p.setFont(font_icon)
                    p.drawText(QtCore.QRectF(cx - spacing/2, rect.top() - 45, spacing, 20),
                               QtCore.Qt.AlignCenter, "👑")
                    p.setFont(font)

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
        # self.feedback_system = InteractionFeedbackSystem(self) # 移除可能有问题的反馈系统

        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        # 设置交互反馈 - 改为仅使用内部动画
        # self.feedback_system.setup_hover_feedback(self, scale_factor=1.08)
        # self.feedback_system.setup_click_feedback(self, with_particles=True)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        prog = self.hover_progress.value
        
        # 应用缩放 (中心缩放)
        if prog > 0:
            scale = 1.0 + 0.08 * prog # 放大 8%
            cx, cy = self.width() / 2, self.height() / 2
            p.translate(cx, cy)
            p.scale(scale, scale)
            p.translate(-cx, -cy)

        # 1. 绘制背景光晕 (Hover) - 莫兰迪蓝光晕
        if prog > 0.01:
            center = QtCore.QPointF(self.width()/2, 40)
            radius = 35 + 5 * prog
            
            # 使用 QLinearGradient 替代 QRadialGradient
            # 某些环境（如远程桌面或虚拟机）对 QRadialGradient 的支持可能不完善，导致 Painter 状态错误
            # 这里改用简单的实心填充+透明度，或者用图片，或者用 QLinearGradient 模拟
            # 为安全起见，我们暂时简化为一个半透明圆
            
            glow_color = QtGui.QColor(168, 216, 234, 76) # 30% alpha
            glow_color.setAlphaF(0.3 * prog)
            
            p.setBrush(glow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(center, radius, radius)

        # 2. 绘制图标
        icon_size = 40 + 4 * prog  # 放大
        icon_rect = QtCore.QRectF(
            (self.width()-icon_size)/2, 40 - icon_size/2, icon_size, icon_size)

        self.draw_icon_shape(p, icon_rect, self.icon_type)

        # 3. 文字信息
        # 周几 - 莫兰迪蓝 90%
        p.setPen(MorandiTheme.COLOR_TEXT_TITLE)
        font = QtGui.QFont("Noto Sans SC", 9)
        p.setFont(font)

        p.drawText(QtCore.QRect(0, 0, self.width(), 20),
                   QtCore.Qt.AlignCenter, self.day_name)

        # 日期 - 莫兰迪蓝 70%
        p.setPen(MorandiTheme.COLOR_TEXT_DATE)
        font.setPixelSize(8)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 65, self.width(), 15),
                   QtCore.Qt.AlignCenter, self.date_str)

        # 时长 - 金色
        p.setPen(MorandiTheme.COLOR_TEXT_VALUE)
        font.setPixelSize(9)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 80, self.width(), 15),
                   QtCore.Qt.AlignCenter, f"{self.hours}h")

    def draw_icon_shape(self, p, rect, type):
        # 统一使用金色主题
        gold = QtGui.QColor("#ffd700")
        
        if type == 'sun':
            p.setBrush(gold)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(4, 4, -4, -4))
            # 光芒
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width()/2
            for i in range(8):
                angle = i * 45
                rad = math.radians(angle)
                ox = cx + math.cos(rad) * (r + 2)
                oy = cy + math.sin(rad) * (r + 2)
                p.setPen(QtGui.QPen(gold, 2))
                p.drawLine(QtCore.QPointF(cx + math.cos(rad)*r, cy + math.sin(rad)*r),
                           QtCore.QPointF(ox, oy))

        elif type == 'star':
            p.setBrush(gold)
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
            p.setBrush(QtGui.QColor(168, 216, 234, 180)) # 莫兰迪蓝
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(2, 6, -2, -6))

        elif type == 'moon':
            p.setBrush(gold.lighter(120)) # 浅金
            p.setPen(QtCore.Qt.NoPen)
            path = QtGui.QPainterPath()
            path.addEllipse(rect)
            cut = QtGui.QPainterPath()
            cut.addEllipse(rect.translated(
                rect.width()*0.3, -rect.height()*0.1))
            path = path.subtracted(cut)
            p.drawPath(path)

    def enterEvent(self, event):
        super().enterEvent(event)
        self.hover_progress.animate_to(1.0, 300)

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

try:
    from ui.component.visual_enhancements.starry_envelope import ReportEnvelopeContainer
except ImportError:
    try:
        from ..visual_enhancements.starry_envelope import ReportEnvelopeContainer
    except ImportError:
        try:
            from .starry_envelope import ReportEnvelopeContainer
        except ImportError:
            from starry_envelope import ReportEnvelopeContainer

# --- 主仪表盘内容 ---


class _WeeklyDashboardContent(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.resize(900, 600)
        
        # 初始化视觉增强组件
        self.animation_engine = PrecisionAnimationEngine(self)
        self.effects_manager = VisualEffectsManager(self)
        
        # 初始化背景星星
        self.stars = self._init_stars()
        self.star_timer = QtCore.QTimer(self)
        self.star_timer.timeout.connect(self.update_stars)
        self.star_timer.start(50) # 20fps

        # 主布局
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(30, 40, 30, 40)
        self.main_layout.setSpacing(20)

        # 左栏
        self.left_panel = AchievementWall()
        # 移除 GraphicsEffect 以修复 Painter 错误
        # self.left_anim_opacity = QtWidgets.QGraphicsOpacityEffect(self.left_panel)
        # self.left_panel.setGraphicsEffect(self.left_anim_opacity)
        # self.left_anim_opacity.setOpacity(0)
        self.left_panel.setWindowOpacity(0.0) # 尝试使用 windowOpacity 或 stylesheet opacity (但这通常对子控件无效)
        # 这里我们使用自定义属性来控制 paintEvent 中的透明度，或者简单地禁用淡入动画

        # 中栏
        self.mid_panel = ComparisonChart()
        # self.mid_anim_opacity = QtWidgets.QGraphicsOpacityEffect(self.mid_panel)
        # self.mid_panel.setGraphicsEffect(self.mid_anim_opacity)
        # self.mid_anim_opacity.setOpacity(0)

        # 右栏
        self.right_panel = QtWidgets.QWidget()
        self.right_panel.setFixedWidth(220)
        r_layout = QtWidgets.QVBoxLayout(self.right_panel)
        r_layout.addWidget(InsightCard(
            "💡 效率高峰期", "上午9-11点", "抓住黄金时段，学霸体质get！"))
        r_layout.addWidget(InsightCard("⚠️ 易分心时段", "下午3点后", "不妨安排轻松任务，灵活调整~"))
        r_layout.addWidget(InsightCard("📈 成长趋势", "本周提升15%", "稳步上升，势头强劲！"))
        r_layout.addStretch()
        
        # 添加 "查看时间轴" 按钮 (新增)
        self.timeline_btn = QtWidgets.QPushButton("查看时间轴")
        self.timeline_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.timeline_btn.setFixedHeight(40)
        # 按钮样式
        self.timeline_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(168, 216, 234, 30);
                border: 1px solid rgba(168, 216, 234, 76);
                border-radius: 20px;
                color: rgba(168, 216, 234, 230);
                font-family: 'Noto Sans SC';
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(168, 216, 234, 64);
                color: #ffd700;
                border: 1px solid rgba(168, 216, 234, 128);
            }}
        """)
        r_layout.addWidget(self.timeline_btn)
        # 连接按钮点击信号
        self.timeline_btn.clicked.connect(self.show_timeline)

        # self.right_anim_opacity = QtWidgets.QGraphicsOpacityEffect(self.right_panel)
        # self.right_panel.setGraphicsEffect(self.right_anim_opacity)
        # self.right_anim_opacity.setOpacity(0)

        # 添加到主布局
        self.main_layout.addWidget(self.left_panel)

        # 分隔线 1 - 莫兰迪蓝
        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.VLine)
        line1.setStyleSheet("background-color: rgba(168, 216, 234, 76);")
        self.main_layout.addWidget(line1)

        self.main_layout.addWidget(self.mid_panel)

        # 分隔线 2
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.VLine)
        line2.setStyleSheet("background-color: rgba(168, 216, 234, 76);")
        self.main_layout.addWidget(line2)

        self.main_layout.addWidget(self.right_panel)

        # 创建启动粒子系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.resize(self.size())

        # 启动入场动画和粒子效果
        self.start_entrance_animation()
        QtCore.QTimer.singleShot(800, self.trigger_startup_particles)
        
    def _init_stars(self):
        stars = []
        # 3颗主星 (80%透明)
        for _ in range(3):
            stars.append({
                'type': 'main',
                'x': random.randint(20, 880),
                'y': random.randint(20, 580),
                'size': 3,
                'delay': random.random() * 2,
                'alpha': 204
            })
        # 5颗背景星 (15%透明)
        for _ in range(5):
            stars.append({
                'type': 'bg',
                'x': random.randint(20, 880),
                'y': random.randint(20, 580),
                'size': 2,
                'delay': random.random() * 5,
                'alpha': 38
            })
        return stars
        
    def update_stars(self):
        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0
        for star in self.stars:
            if star['type'] == 'main':
                # 2秒周期 80% -> 100% -> 80% (204 -> 255 -> 204)
                t = (current_time + star['delay']) % 2.0
                norm = t / 1.0 if t < 1.0 else (2.0 - t) / 1.0
                # 限制 alpha 值在 0-255 范围内
                alpha_val = int(204 + (51 * norm))
                star['alpha'] = max(0, min(255, alpha_val))
            else:
                # 8秒周期
                t = (current_time + star['delay']) % 8.0
                norm = t / 4.0 if t < 4.0 else (8.0 - t) / 4.0
                # 限制 alpha 值在 0-255 范围内
                alpha_val = int(20 + (30 * norm))
                star['alpha'] = max(0, min(255, alpha_val))
        self.update()

    def show_timeline(self):
        """显示时间轴窗口"""
        try:
            # 延迟导入以避免循环依赖
            # 尝试从同级目录导入
            if __name__ == "__main__":
                from daily_sum import TimelineView
            else:
                from .daily_sum import TimelineView
                
            self.timeline_window = TimelineView()
            self.timeline_window.show()
        except ImportError:
            # Fallback for different execution contexts
            try:
                from ui.component.report.daily_sum import TimelineView
                self.timeline_window = TimelineView()
                self.timeline_window.show()
            except Exception as e:
                print(f"Import Error: {e}")
        except Exception as e:
            print(f"Error showing timeline: {e}")

    def paintEvent(self, event):
        # 绘制莫兰迪主题背景
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # 径向渐变背景
        rect = self.rect()
        gradient = QtGui.QRadialGradient(rect.center(), max(rect.width(), rect.height()) / 1.2)
        gradient.setColorAt(0, MorandiTheme.COLOR_BG_CENTER)
        gradient.setColorAt(1, MorandiTheme.COLOR_BG_EDGE)
        
        p.setBrush(gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(rect, 12, 12)
        
        # 绘制背景星星
        for star in self.stars:
            c = QtGui.QColor("#ffd700")
            c.setAlpha(int(star['alpha']))
            p.setBrush(c)
            p.drawEllipse(QtCore.QPointF(star['x'], star['y']), star['size'], star['size'])

        # 边框 (30%透明)
        p.setPen(QtGui.QPen(MorandiTheme.COLOR_BORDER, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12, 12)
        
        # 内阴影 (模拟: inset 0 0 20px rgba(168, 216, 234, 0.05))
        # 简单画一个淡色框
        inner_pen = QtGui.QPen(QtGui.QColor(168, 216, 234, 12), 4)
        p.setPen(inner_pen)
        p.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 10, 10)

    def start_entrance_animation(self):
        # 暂时禁用淡入动画以修复 Painter 错误
        pass
        # 依次淡入
        # 左栏 0ms
        # self.anim1 = QtCore.QPropertyAnimation(
        #     self.left_anim_opacity, b"opacity")
        # self.anim1.setDuration(600)
        # self.anim1.setStartValue(0)
        # self.anim1.setEndValue(1)
        # self.anim1.start()

        # 中栏 200ms
        # self.anim2 = QtCore.QPropertyAnimation(
        #     self.mid_anim_opacity, b"opacity")
        # self.anim2.setDuration(600)
        # self.anim2.setStartValue(0)
        # self.anim2.setEndValue(1)
        # QtCore.QTimer.singleShot(200, self.anim2.start)

        # 右栏 400ms
        # self.anim3 = QtCore.QPropertyAnimation(
        #     self.right_anim_opacity, b"opacity")
        # self.anim3.setDuration(600)
        # self.anim3.setStartValue(0)
        # self.anim3.setEndValue(1)
        # QtCore.QTimer.singleShot(400, self.anim3.start)

    def trigger_startup_particles(self):
        """触发启动粒子庆祝效果"""
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.particle_system.trigger_startup_effect(center)

    def resizeEvent(self, event):
        """窗口大小改变时调整粒子系统"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_system'):
            self.particle_system.resize(self.size())


class WeeklyDashboard(ReportEnvelopeContainer):
    clicked = Signal()

    def __init__(self):
        super().__init__(expanded_height=600)
        self.resize(900, 280)
        self.drag_start_pos = None

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.content = _WeeklyDashboardContent()
        self.set_content(self.content)
        
        # 居中显示
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            self.move(screen.geometry().center() - self.rect().center())
            
        # 连接折叠状态改变信号，实现动态移动
        # 注意：WeeklyDashboard 继承自 ReportEnvelopeContainer，它直接就是容器
        self.stateChanged.connect(self._on_collapse_state_changed)
        
        # 兼容性别名，以防某些代码（如测试代码）尝试访问 collapsible_container
        self.collapsible_container = self

    def _on_collapse_state_changed(self, is_expanded: bool):
        """折叠状态改变时调整窗口位置"""
        screen = QtGui.QGuiApplication.primaryScreen()
        if not screen:
            return
            
        screen_center = screen.geometry().center()
        
        if is_expanded:
            # 展开时：向上偏移 200px
            # 注意：此时窗口大小已经在动画中改变，这里我们需要基于最终大小计算位置
            # 或者简单地：直接从中心点向上偏移固定距离
            
            # 目标位置：屏幕中心 - 窗口中心(展开后) - 偏移量
            # 由于动画是平滑的，我们这里直接设定目标位置
            
            # 计算展开后的中心点偏移
            # 我们希望内容看起来是向上生长的，或者整体上移
            
            target_pos = screen_center - QtCore.QPoint(self.width() // 2, self.height() // 2) - QtCore.QPoint(0, 200)
            
            # 使用动画平滑移动窗口
            self.pos_anim = QtCore.QPropertyAnimation(self, b"pos")
            self.pos_anim.setDuration(500)
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(target_pos)
            self.pos_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            self.pos_anim.start()
            
        else:
            # 折叠（收起）时：回到屏幕正中央
            # 此时窗口高度会变回信封高度
            
            # 目标位置：屏幕中心 - 信封中心
            # 信封高度通常较小 (例如 280)
            
            # 重新计算居中位置（基于当前信封大小）
            # 注意：CollapsibleContainer 的动画可能还在进行，
            # 我们假设最终高度是信封高度
            
            # 这里稍微有些复杂，因为高度在变，位置也在变。
            # 为了简单可靠，我们计算"视觉中心"复位。
            
            target_pos = screen_center - QtCore.QPoint(self.width() // 2, self.state.current_height // 2)
            
            self.pos_anim = QtCore.QPropertyAnimation(self, b"pos")
            self.pos_anim.setDuration(500)
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(target_pos)
            self.pos_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            self.pos_anim.start()

    def changeEvent(self, event):
        """处理窗口状态变化"""
        if event.type() == QtCore.QEvent.ActivationChange:
            # 如果失去焦点，关闭窗口
            # 但要排除一种情况：如果失去焦点是因为打开了子窗口（如 InsightCard 的详细建议弹窗），则不应该关闭
            if not self.isActiveWindow():
                # 检查是否有模态对话框或子窗口处于活动状态
                # 注意：Qt 的 activeModalWidget() 可能在某些情况下不准确
                # 我们可以遍历应用程序的所有顶层窗口，看是否有我们的子窗口处于激活状态
                
                app = QtWidgets.QApplication.instance()
                active_window = app.activeWindow()
                
                should_close = True
                
                if active_window:
                    # 1. 检查是否是 SuggestionDialog (通过类名判断，避免导入依赖)
                    if "SuggestionDialog" in active_window.__class__.__name__:
                        should_close = False
                    
                    # 2. 检查 active_window 是否是我们的子窗口或后代
                    elif active_window.parent() == self or self.isAncestorOf(active_window):
                        should_close = False
                        
                    # 3. 检查 active_window 的 transientParent 是否是我们
                    # (对话框通常设置 transient parent)
                    elif active_window.window().windowHandle() and \
                         active_window.window().windowHandle().transientParent() == self.windowHandle():
                         should_close = False

                if should_close:
                    self.close()
                    
        super().changeEvent(event)
    
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
