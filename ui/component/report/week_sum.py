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
        self.setFixedSize(200, 100) # 减小高度，去掉多余空间
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
        # 悬停时展开高度以显示描述和详情提示
        if progress > 0.05:
            # 动态调整高度: 基础高度 + 额外高度 * 进度
            current_height = 100 + 60 * progress
            self.setFixedHeight(int(current_height))
        else:
            self.setFixedHeight(100)
            
        offset_y = -5 * progress  # 悬停上浮 5px

        # 背景区域
        rect = QtCore.QRectF(
            5, 5 + offset_y, self.width()-10, self.height()-10)

        # 莫兰迪背景 (透明度8%-15%)
        bg_color = QtGui.QColor(MorandiTheme.COLOR_BG_PANEL)
        bg_color.setAlpha(30) # ~12%
        p.setBrush(bg_color)

        # 边框 (悬停时发光)
        if progress > 0.1:
            border_color = QtGui.QColor("#5D4037")
            border_color.setAlphaF(0.6 * progress)
            p.setPen(QtGui.QPen(border_color, 2 + progress))
            
            # 悬停光晕
            glow_rect = rect.adjusted(-2, -2, 2, 2)
            glow_color = QtGui.QColor(MorandiTheme.COLOR_PRIMARY_LIGHT)
            glow_color.setAlpha(76)
            p.setBrush(glow_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(glow_rect, 12, 12)
            p.setBrush(bg_color) # 恢复背景
            
        else:
            # 边框透明度 30%
            border_color = QtGui.QColor(MorandiTheme.COLOR_BORDER)
            border_color.setAlpha(76)
            p.setPen(QtGui.QPen(border_color, 1))

        p.drawRoundedRect(rect, 12, 12)

        # 文字绘制
        # 标题 - 莫兰迪蓝 100%
        p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_TITLE))
        font = QtGui.QFont("Noto Sans SC", 11, QtGui.QFont.Bold)
        p.setFont(font)
        p.drawText(rect.adjusted(15, 15, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.title)

        # 星星图标 (如果在标题旁) - 这里直接绘制在标题右侧
        if "✨" not in self.title: 
            pass

        # 副标题 (数据值) + 发光
        font_sub = QtGui.QFont("Noto Sans SC", 12)
        p.setFont(font_sub)
        p.setPen(QtGui.QColor("#5D4037"))
        
        # 绘制文字阴影 (模拟发光)
        p.save()
        p.translate(0, 0)
        p.restore()
        
        p.drawText(rect.adjusted(15, 40, -15, 0),
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, self.subtitle)

        # 描述文字 - 莫兰迪蓝 80% (仅在悬停时显示)
        if progress > 0.05:
            font_desc = QtGui.QFont("Noto Sans SC", 11)
            p.setFont(font_desc)
            p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_SECONDARY))
            p.setOpacity(progress)
            rect_desc = rect.adjusted(15, 65, -15, -30)
            p.drawText(rect_desc, QtCore.Qt.AlignLeft |
                       QtCore.Qt.TextWordWrap, self.desc)
            p.setOpacity(1.0)

        # 底部提示 - 悬停时显示
        if progress > 0.05:
            p.setOpacity(progress)
            font_hint = QtGui.QFont("Noto Sans SC", 10)
            p.setFont(font_hint)
            p.setPen(QtGui.QColor("#5D4037"))
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

# --- 左栏：核心洞察 (WeeklySummaryView) ---

class SummaryCard(QtWidgets.QWidget):
    def __init__(self, data):
        super().__init__()
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # 动画相关
        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)
        
        self.data = data
        self.setFixedHeight(110) # 固定高度
        
        # 字体预设
        self.font_icon = QtGui.QFont("Segoe UI Emoji", 18)
        self.font_title = QtGui.QFont("Noto Sans SC", 10, QtGui.QFont.Bold)
        self.font_value = QtGui.QFont("Noto Sans SC", 16, QtGui.QFont.Bold)
        self.font_sub = QtGui.QFont("Noto Sans SC", 9)
        self.font_desc = QtGui.QFont("Noto Sans SC", 9)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect()
        progress = self.hover_progress.value
        
        # 1. 背景
        # 基础背景: 莫兰迪蓝 10%
        bg_color = QtGui.QColor(MorandiTheme.COLOR_BG_PANEL)
        bg_color.setAlpha(25)
        # 悬停时加深
        if progress > 0:
            bg_color.setAlpha(25 + int(20 * progress))
            
        p.setBrush(bg_color)
        
        # 边框
        # 使用主题颜色映射
        border_color = QtGui.QColor(self.data.get('color', MorandiTheme.COLOR_BORDER))
        border_color.setAlphaF(0.3 + 0.4 * progress) # 30% -> 70%
        p.setPen(QtGui.QPen(border_color, 1 + progress))
        
        p.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)
        
        # 2. 内容绘制
        # 图标
        p.setFont(self.font_icon)
        p.setPen(QtCore.Qt.NoPen) # Emoji通常不需要Pen颜色，或者跟随系统
        # 注意：Qt绘制Emoji可能需要特定字体支持，这里假设Segoe UI Emoji可用
        p.setPen(QtGui.QColor(0,0,0, 220)) 
        p.drawText(QtCore.QRect(15, 15, 40, 40), QtCore.Qt.AlignCenter, self.data['icon'])
        
        # 标题
        p.setFont(self.font_title)
        p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_TITLE))
        p.drawText(QtCore.QRect(60, 15, 200, 20), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.data['title'])
        
        # 数值
        p.setFont(self.font_value)
        val_color = QtGui.QColor(self.data.get('color', "#5D4037"))
        p.setPen(val_color)
        p.drawText(QtCore.QRect(60, 38, 200, 30), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.data['value'])
        
        # 副标题 (显示在数值右侧或下方，这里放右侧)
        # p.setFont(self.font_sub)
        # p.setPen(QtGui.QColor(165, 214, 167, 200))
        # text_width = QtGui.QFontMetrics(self.font_value).horizontalAdvance(self.data['value'])
        # p.drawText(QtCore.QRect(60 + text_width + 10, 42, 150, 20), 
        #            QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom, self.data['subtitle'])
        
        # 描述 (底部)
        p.setFont(self.font_desc)
        p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_SECONDARY))
        p.drawText(QtCore.QRect(15, 75, self.width()-30, 30), 
                   QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter | QtCore.Qt.TextWordWrap, 
                   self.data['description'])

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)


class WeeklySummaryView(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(380, 400)
        
        # 数据生成 (模拟 generate_weekly_summary_v1)
        self.summary_data = {
             "title": "本周核心洞察",
             "cards": [
                 {
                     "icon": "🎯",
                     "title": "专注得分",
                     "value": "82分",
                     "subtitle": "连续5天达标",
                     "description": "你的专注力超越了78%的用户，保持这个节奏！",
                     "color": MorandiTheme.COLOR_PRIMARY_DARK.name() # 绿色 -> 森林绿
                 },
                 {
                     "icon": "⚡",
                     "title": "效率峰值",
                     "value": "09:00-11:00",
                     "subtitle": "平均专注6.0小时",
                     "description": "这个时段你的代码产出量是平时的2.3倍",
                     "color": MorandiTheme.COLOR_WARNING.name() # 橙色 -> 金色/警告色
                 },
                 {
                     "icon": "🛡️",
                     "title": "自控力挑战",
                     "value": "15:00-17:00",
                     "subtitle": "分心次数增加2次",
                     "description": "AI帮你截停了3次无效浏览，夺回45分钟",
                     "color": MorandiTheme.HEX_BLUE_LIGHT # 蓝色 -> 莫兰迪蓝
                 }
             ]
         }

        # 布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QtWidgets.QLabel(self.summary_data["title"])
        title_label.setStyleSheet("""
            color: #5D4037;
            font-family: 'Noto Sans SC';
            font-size: 18px;
            font-weight: bold;
            background: transparent;
        """)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(10)
        
        # 卡片列表
        for card_data in self.summary_data["cards"]:
            card = SummaryCard(card_data)
            layout.addWidget(card)
            
        layout.addStretch()

    def paintEvent(self, event):
        # 绘制简单的背景或边框辅助查看区域 (可选)
        pass

# --- 左栏：成就墙 (改为 WeeklyTrendChart) ---

class WeeklyTrendChart(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self.setMinimumHeight(300)
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 动画变量
        self.anim_progress = AnimatedValue(0.0)
        self.anim_progress.valueChanged.connect(self.update)
        # 启动入场动画
        self.anim_progress.animate_to(1.0, 1000, 200, QtCore.QEasingCurve.OutQuart)
        
        # 悬停点索引
        self.hovered_index = -1

        # 数据: (周几, 日期, 时长, 评级, 图标类型)
        self.data = [
            ("周一", "12/8", 4.2, "专注", "sun"),
            ("周二", "12/9", 6.1, "巅峰", "sun"),
            ("周三", "12/10", 5.8, "优秀", "sun"),
            ("周四", "12/11", 2.5, "放松", "cloud"),
            ("周五", "12/12", 5.2, "良好", "sun"),
            ("周六", "12/13", 3.0, "休息", "star"),
            ("周日", "12/14", 4.5, "恢复", "moon"),
        ]
        
        self.max_hours = 8.0 # Y轴最大值

    def mouseMoveEvent(self, event):
        # 简单的悬停检测
        pos = event.pos()
        w = self.width()
        spacing = w / len(self.data)
        margin_left = spacing / 2
        
        index = int((pos.x()) / spacing)
        if 0 <= index < len(self.data):
            self.hovered_index = index
            self.update()
        else:
            self.hovered_index = -1
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered_index = -1
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 绘图区域参数
        padding_top = 60
        padding_bottom = 40
        graph_h = h - padding_top - padding_bottom
        
        spacing = w / len(self.data)
        
        # 1. 绘制折线
        points = []
        progress = self.anim_progress.value
        
        # 颜色定义
        color_main = QtGui.QColor(MorandiTheme.COLOR_PRIMARY_DARK)
        color_gold = QtGui.QColor("#FFC400")
        
        for i, item in enumerate(self.data):
            hours = item[2]
            cx = spacing * i + spacing / 2
            
            # 计算Y坐标 (0在下方)
            # 加上动画效果: 高度从0长到目标值
            target_y_ratio = hours / self.max_hours
            current_y_ratio = target_y_ratio * progress
            
            cy = h - padding_bottom - (current_y_ratio * graph_h)
            points.append(QtCore.QPointF(cx, cy))
            
        if len(points) > 1:
            # 绘制连线 - 金色
            p.setPen(QtGui.QPen(color_gold, 2))
            path = QtGui.QPainterPath()
            path.moveTo(points[0])
            for pt in points[1:]:
                path.lineTo(pt)
            p.drawPath(path)
            
            # 绘制下方填充 (渐变)
            fill_path = QtGui.QPainterPath(path)
            fill_path.lineTo(points[-1].x(), h - padding_bottom)
            fill_path.lineTo(points[0].x(), h - padding_bottom)
            fill_path.closeSubpath()
            
            grad = QtGui.QLinearGradient(0, padding_top, 0, h - padding_bottom)
            c_start = QtGui.QColor(color_gold)
            c_start.setAlpha(40) # 15%左右
            c_end = QtGui.QColor(color_gold)
            c_end.setAlpha(0)
            grad.setColorAt(0, c_start)
            grad.setColorAt(1, c_end)
            p.setBrush(grad)
            p.setPen(QtCore.Qt.NoPen)
            p.drawPath(fill_path)

        # 2. 绘制每个点的内容 (图标, 文字)
        for i, (day, date_str, hours, lvl, icon_type) in enumerate(self.data):
            pt = points[i]
            cx, cy = pt.x(), pt.y()
            
            is_hovered = (i == self.hovered_index)
            
            # 绘制点 - 金色实心
            p.setBrush(color_gold)
            p.setPen(QtCore.Qt.NoPen)
            dot_size = 6 if not is_hovered else 9
            p.drawEllipse(QtCore.QPointF(cx, cy), dot_size/2, dot_size/2)
            
            # 绘制上方图标
            # 稍微上移一点
            icon_y = cy - 25
            icon_size = 24 if not is_hovered else 30
            icon_rect = QtCore.QRectF(cx - icon_size/2, icon_y - icon_size/2, icon_size, icon_size)
            
            self.draw_icon_shape(p, icon_rect, icon_type)
            
            # 绘制上方时长文字
            p.setPen(color_gold)
            font_val = QtGui.QFont("Noto Sans SC", 9, QtGui.QFont.Bold)
            p.setFont(font_val)
            p.drawText(QtCore.QRectF(cx - 30, icon_rect.top() - 20, 60, 20), 
                       QtCore.Qt.AlignCenter, f"{hours}h")
            
            # 绘制下方日期文字
            # 周几
            p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_TITLE)) # Cream/Beige
            font_day = QtGui.QFont("Noto Sans SC", 9)
            p.setFont(font_day)
            p.drawText(QtCore.QRectF(cx - 30, h - padding_bottom + 5, 60, 20),
                       QtCore.Qt.AlignCenter, day)
            
            # 日期
            p.setPen(QtGui.QColor(MorandiTheme.COLOR_TEXT_SECONDARY)) # Secondary
            font_date = QtGui.QFont("Noto Sans SC", 8)
            p.setFont(font_date)
            p.drawText(QtCore.QRectF(cx - 30, h - padding_bottom + 22, 60, 15),
                       QtCore.Qt.AlignCenter, date_str)

    def draw_icon_shape(self, p, rect, type):
        gold = QtGui.QColor("#FFC400")
        
        if type == 'sun':
            p.setBrush(gold)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(2, 2, -2, -2))
            # 光芒
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width()/2 - 1
            for i in range(8):
                angle = i * 45
                rad = math.radians(angle)
                ox = cx + math.cos(rad) * (r + 1.5)
                oy = cy + math.sin(rad) * (r + 1.5)
                p.setPen(QtGui.QPen(gold, 1.5))
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
            p.setBrush(QtGui.QColor(MorandiTheme.COLOR_PRIMARY_LIGHT)) # Muted Teal
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(rect.adjusted(1, 3, -1, -3))

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


class WeeklyReportMain(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.resize(1000, 600)
        
        # 状态标记：是否已展开左右面板
        self.is_left_expanded = False
        self.is_right_expanded = False
        
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

        # 左栏 (原中栏成就墙 ComparisonChart -> WeeklySummaryView)
        self.left_panel = WeeklySummaryView()
        # 初始隐藏左栏
        self.left_panel.setMinimumWidth(0)
        self.left_panel.setMaximumWidth(0)
        
        # 移除 GraphicsEffect 以修复 Painter 错误
        # self.left_anim_opacity = QtWidgets.QGraphicsOpacityEffect(self.left_panel)
        # self.left_panel.setGraphicsEffect(self.left_anim_opacity)
        # self.left_anim_opacity.setOpacity(0)
        self.left_panel.setWindowOpacity(0.0) # 尝试使用 windowOpacity 或 stylesheet opacity (但这通常对子控件无效)
        # 这里我们使用自定义属性来控制 paintEvent 中的透明度，或者简单地禁用淡入动画

        # 中栏 (原左栏本周记录 AchievementWall)
        # 创建中间容器，用于垂直排列成就墙和下方按钮
        self.mid_container = QtWidgets.QWidget()
        self.mid_container.setFixedWidth(280)
        self.mid_layout = QtWidgets.QVBoxLayout(self.mid_container)
        # 增加顶部边距，避开标题 (标题高度约90+40=130，这里设置80+40=120，略有重叠或紧凑，视情况调整)
        # 考虑到标题框的实际位置，下移 100px 比较稳妥
        # 用户要求再下移一点，改为 140 -> 180 -> 150 (上移以平衡空间)
        self.mid_layout.setContentsMargins(0, 60, 0, 0)
        self.mid_layout.setSpacing(15)

        self.mid_panel = WeeklyTrendChart()
        self.mid_layout.addWidget(self.mid_panel)
        
        # 添加两个功能按钮
        # 按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: {MorandiTheme.COLOR_PRIMARY_LIGHT.name()};
                border: 1px solid {MorandiTheme.COLOR_BORDER.name()};
                border-radius: 12px;
                color: #FFC400;
                font-family: 'Noto Sans SC';
                font-size: 14px;
                font-weight: bold;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: {MorandiTheme.COLOR_PRIMARY_DARK.name()};
                border: 1px solid #FFC400;
            }}
        """
        
        self.btn_summary = QtWidgets.QPushButton("核心洞察")
        self.btn_summary.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_summary.setStyleSheet(btn_style)
        self.btn_summary.clicked.connect(self.toggle_left_panel)
        self.mid_layout.addWidget(self.btn_summary)

        self.btn_ai_suggestion = QtWidgets.QPushButton("AI建议")
        self.btn_ai_suggestion.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_ai_suggestion.setStyleSheet(btn_style)
        self.btn_ai_suggestion.clicked.connect(self.toggle_right_panel)
        self.mid_layout.addWidget(self.btn_ai_suggestion)
        
        self.mid_layout.addStretch()

        # 连接点击信号以触发展开动画 (可选：点击面板本身也展开全部，或取消此行为)
        # self.mid_panel.clicked.connect(self.expand_panels) # 取消点击面板展开全部的行为，改由按钮控制

        # 右栏
        self.right_panel = QtWidgets.QWidget()
        # 初始隐藏右栏
        self.right_panel.setFixedWidth(0) # 初始宽度0
        
        r_layout = QtWidgets.QVBoxLayout(self.right_panel)
        # 增加顶部边距，留出标题空间
        r_layout.setContentsMargins(0, 40, 0, 0)
        # 增加栏目间距
        r_layout.setSpacing(30) # 10 -> 20 -> 30

        # 添加 "AI建议" 标题
        title_label = QtWidgets.QLabel("AI建议")
        title_label.setStyleSheet("""
            color: #5D4037;
            font-family: 'Noto Sans SC';
            font-size: 18px;
            font-weight: bold;
            background: transparent;
        """)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        r_layout.addWidget(title_label)
        
        r_layout.addSpacing(10)
        
        r_layout.addWidget(InsightCard(
            "💡 效率高峰期", "上午9-11点", "抓住黄金时段，学霸体质get！"))
        r_layout.addWidget(InsightCard("⚠️ 易分心时段", "下午3点后", "不妨安排轻松任务，灵活调整~"))
        r_layout.addWidget(InsightCard("📈 成长趋势", "本周提升15%", "稳步上升，势头强劲！"))
        r_layout.addStretch()

        # self.right_anim_opacity = QtWidgets.QGraphicsOpacityEffect(self.right_panel)
        # self.right_panel.setGraphicsEffect(self.right_anim_opacity)
        # self.right_anim_opacity.setOpacity(0)

        # 添加到主布局
        self.main_layout.addWidget(self.left_panel)

        # 分隔线 1 - 莫兰迪蓝
        self.line1 = QtWidgets.QFrame()
        self.line1.setFrameShape(QtWidgets.QFrame.VLine)
        self.line1.setStyleSheet(f"background-color: {MorandiTheme.COLOR_BORDER.name()};")
        # 初始隐藏分隔线
        self.line1.hide()
        self.main_layout.addWidget(self.line1)

        self.main_layout.addWidget(self.mid_container)

        # 分隔线 2
        self.line2 = QtWidgets.QFrame()
        self.line2.setFrameShape(QtWidgets.QFrame.VLine)
        self.line2.setStyleSheet(f"background-color: {MorandiTheme.COLOR_BORDER.name()};")
        # 初始隐藏分隔线
        self.line2.hide()
        self.main_layout.addWidget(self.line2)

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
            self.timeline_window.show_timeline()
        except ImportError:
            # Fallback for different执行 contexts
            try:
                from ui.component.report.daily_sum import TimelineView
                self.timeline_window = TimelineView()
                self.timeline_window.show_timeline()
            except Exception as e:
                print(f"Import Error: {e}")
        except Exception as e:
            print(f"Error showing timeline: {e}")

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QtGui.QColor("#7AA97D"))
        gradient.setColorAt(1, QtGui.QColor("#C0D6C5"))
        
        p.setBrush(gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(rect, 12, 12)
        
        # 绘制背景星星
        for star in self.stars:
            c = QtGui.QColor("#5D4037")
            c.setAlpha(int(star['alpha']))
            p.setBrush(c)
            p.drawEllipse(QtCore.QPointF(star['x'], star['y']), star['size'], star['size'])

        p.setPen(QtGui.QPen(MorandiTheme.COLOR_BORDER, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12, 12)
        
        # 内阴影 (模拟: inset 0 0 20px rgba(165, 214, 167, 0.05))
        # 简单画一个淡色框
        inner_pen = QtGui.QPen(QtGui.QColor(MorandiTheme.COLOR_PRIMARY_LIGHT), 4)
        inner_pen.color().setAlpha(12)
        p.setPen(inner_pen)
        p.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 10, 10)

        # 绘制顶部中央标题框
        # 修改定位逻辑：获取 mid_panel 在 WeeklyReportMain 中的绝对位置中心
        # 这样即使左侧趋势图展开导致布局移动，标题也会跟随移动，保持相对位置不变
        
        # 1. 获取 mid_panel 在 mid_container 中的中心点
        panel_center_in_container = self.mid_panel.geometry().center().x()
        # 2. 获取 mid_container 在 WeeklyReportMain (self) 中的 x 坐标
        container_x = self.mid_container.geometry().x()
        
        target_center_x = container_x + panel_center_in_container
        
        title_rect_w, title_rect_h = 300, 90
        top_margin = 40  # 与主布局顶部边距一致
        
        title_rect = QtCore.QRectF(target_center_x - title_rect_w / 2,
                                   top_margin,
                                   title_rect_w, title_rect_h)

        # 标题文字
        p.setPen(QtGui.QColor("#8D6E63"))
        font_title = QtGui.QFont("Noto Sans SC", 24, QtGui.QFont.Bold)
        p.setFont(font_title)
        p.drawText(title_rect, QtCore.Qt.AlignCenter, "本周战绩")

        # 装饰线 - 莫兰迪蓝 30%
        p.setPen(QtGui.QPen(QtGui.QColor(MorandiTheme.COLOR_BORDER), 2))
        p.drawLine(QtCore.QPointF(title_rect.left() + 40, title_rect.bottom() - 20),
                   QtCore.QPointF(title_rect.right() - 40, title_rect.bottom() - 20))

    def toggle_left_panel(self):
        """切换左侧面板（核心洞察）"""
        target_left_width = 380
        top_window = self.window()
        
        if not self.is_left_expanded:
            # 展开左侧
            self.is_left_expanded = True
            self.line1.show()
            
            # 1. 窗口扩展
            if top_window:
                current_geo = top_window.geometry()
                # 向左扩展
                target_geo = QtCore.QRect(
                    current_geo.x() - target_left_width,
                    current_geo.y(),
                    current_geo.width() + target_left_width,
                    current_geo.height()
                )
                self.anim_window_l = QtCore.QPropertyAnimation(top_window, b"geometry")
                self.anim_window_l.setDuration(600)
                self.anim_window_l.setStartValue(current_geo)
                self.anim_window_l.setEndValue(target_geo)
                self.anim_window_l.setEasingCurve(QtCore.QEasingCurve.OutQuart)
                self.anim_window_l.start()

            # 2. 左栏动画
            self.left_panel.setMinimumWidth(0)
            self.anim_left = QtCore.QPropertyAnimation(self.left_panel, b"maximumWidth")
            self.anim_left.setDuration(600)
            self.anim_left.setStartValue(0)
            self.anim_left.setEndValue(target_left_width)
            self.anim_left.setEasingCurve(QtCore.QEasingCurve.OutQuart)
            self.anim_left.finished.connect(lambda: self.left_panel.setMinimumWidth(target_left_width))
            self.anim_left.start()
            
            self.btn_summary.setText("收起洞察")
            
        else:
            # 收起左侧
            self.is_left_expanded = False
            # self.line1.hide() # 动画结束后隐藏
            
            # 1. 窗口收缩
            if top_window:
                current_geo = top_window.geometry()
                # 向右收缩 (x 增加，width 减小)
                target_geo = QtCore.QRect(
                    current_geo.x() + target_left_width,
                    current_geo.y(),
                    current_geo.width() - target_left_width,
                    current_geo.height()
                )
                self.anim_window_l = QtCore.QPropertyAnimation(top_window, b"geometry")
                self.anim_window_l.setDuration(600)
                self.anim_window_l.setStartValue(current_geo)
                self.anim_window_l.setEndValue(target_geo)
                self.anim_window_l.setEasingCurve(QtCore.QEasingCurve.OutQuart)
                self.anim_window_l.start()

            # 2. 左栏动画
            self.left_panel.setMinimumWidth(0)
            self.left_panel.setMaximumWidth(target_left_width)
            self.anim_left = QtCore.QPropertyAnimation(self.left_panel, b"maximumWidth")
            self.anim_left.setDuration(600)
            self.anim_left.setStartValue(target_left_width)
            self.anim_left.setEndValue(0)
            self.anim_left.setEasingCurve(QtCore.QEasingCurve.OutQuart)
            self.anim_left.finished.connect(self.line1.hide)
            self.anim_left.start()
            
            self.btn_summary.setText("核心洞察")

    def toggle_right_panel(self):
        """切换右侧面板（AI建议）"""
        target_right_width = 220
        top_window = self.window()
        
        if not self.is_right_expanded:
            # 展开右侧
            self.is_right_expanded = True
            self.line2.show()
            
            # 1. 窗口扩展
            if top_window:
                current_geo = top_window.geometry()
                # 向右扩展 (x 不变，width 增加)
                target_geo = QtCore.QRect(
                    current_geo.x(),
                    current_geo.y(),
                    current_geo.width() + target_right_width,
                    current_geo.height()
                )
                self.anim_window_r = QtCore.QPropertyAnimation(top_window, b"geometry")
                self.anim_window_r.setDuration(600)
                self.anim_window_r.setStartValue(current_geo)
                self.anim_window_r.setEndValue(target_geo)
                self.anim_window_r.setEasingCurve(QtCore.QEasingCurve.OutQuart)
                self.anim_window_r.start()

            # 2. 右栏动画
            self.right_panel.setMinimumWidth(0)
            self.anim_right = QtCore.QPropertyAnimation(self.right_panel, b"maximumWidth")
            self.anim_right.setDuration(600)
            self.anim_right.setStartValue(0)
            self.anim_right.setEndValue(target_right_width)
            self.anim_right.setEasingCurve(QtCore.QEasingCurve.OutQuart)
            self.anim_right.finished.connect(lambda: self.right_panel.setMinimumWidth(target_right_width))
            self.anim_right.start()
            
            self.btn_ai_suggestion.setText("收起建议")
            
        else:
            # 收起右侧
            self.is_right_expanded = False
            
            # 1. 窗口收缩
            if top_window:
                current_geo = top_window.geometry()
                # 向左收缩 (x 不变，width 减小)
                target_geo = QtCore.QRect(
                    current_geo.x(),
                    current_geo.y(),
                    current_geo.width() - target_right_width,
                    current_geo.height()
                )
                self.anim_window_r = QtCore.QPropertyAnimation(top_window, b"geometry")
                self.anim_window_r.setDuration(600)
                self.anim_window_r.setStartValue(current_geo)
                self.anim_window_r.setEndValue(target_geo)
                self.anim_window_r.setEasingCurve(QtCore.QEasingCurve.OutQuart)
                self.anim_window_r.start()

            # 2. 右栏动画
            self.right_panel.setMinimumWidth(0)
            self.right_panel.setMaximumWidth(target_right_width)
            self.anim_right = QtCore.QPropertyAnimation(self.right_panel, b"maximumWidth")
            self.anim_right.setDuration(600)
            self.anim_right.setStartValue(target_right_width)
            self.anim_right.setEndValue(0)
            self.anim_right.setEasingCurve(QtCore.QEasingCurve.OutQuart)
            self.anim_right.finished.connect(self.line2.hide)
            self.anim_right.start()
            
            self.btn_ai_suggestion.setText("AI建议")

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
        self.resize(1000, 600)
        self.drag_start_pos = None

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.toggle_button.set_gradient("#7AA97D", "#C0D6C5")
        self.content = WeeklyReportMain()
        self.set_content(self.content)
        
        # 初始宽度调整为只显示中间面板 (340px = 280 + 30 + 30)
        # 高度增加以容纳标题、成就墙和按钮 (原280 -> 520 -> 550 -> 600)
        self.resize(340, 600)
        
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
            
            # 此时 content 可能还没有水平展开，宽度较窄
            # 如果 content 已经展开了，宽度是 1000
            # 我们取当前宽度即可
            
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
