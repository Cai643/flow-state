import sys
import math
import random
import numpy as np
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
    Property = QtCore.Property
    is_pyside6 = True
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    Property = QtCore.pyqtProperty
    is_pyside6 = False

try:
    # Try the generic backend first (available in newer matplotlib)
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    if is_pyside6:
        try:
            from matplotlib.backends.backend_qt6agg import FigureCanvasQTAgg as FigureCanvas
        except ImportError:
            # Fallback to qt5agg if qt6agg is missing
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    else:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 导入视觉增强组件
try:
    # 尝试直接绝对导入 (当作为模块运行或项目根目录在path中时)
    from ui.component.visual_enhancements.startup_particle_system import StartupParticleSystem
    from ui.component.visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
except ImportError:
    # 如果失败，可能是直接运行此文件，需要手动添加项目根目录到 path
    import sys
    import os
    
    # 获取当前文件所在目录: .../ui/component/report
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 推导项目根目录: .../flow_state
    # report -> component -> ui -> flow_state
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)  # 插入到最前面以优先搜索
        
    try:
        # 添加路径后再次尝试绝对导入
        from ui.component.visual_enhancements.startup_particle_system import StartupParticleSystem
        from ui.component.visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
    except ImportError:
        try:
            # 尝试相对导入 (仅当在包内时有效)
            from ..visual_enhancements.startup_particle_system import StartupParticleSystem
            from ..visual_enhancements.precision_animation_engine import PrecisionAnimationEngine
        except ImportError:
            # 如果都失败，创建占位符类以防止崩溃
            print("Warning: Could not import visual enhancement components. Using placeholders.")
            
            class StartupParticleSystem(QtWidgets.QWidget):
                def __init__(self, parent=None):
                    super().__init__(parent)
                def create_particle_burst(self, center, count): pass
                def trigger_startup_effect(self, center): pass
                def show(self): pass
                def hide(self): pass

            class PrecisionAnimationEngine:
                def __init__(self, parent=None): pass
                def create_button_press_animation(self, widget): return None
                def create_combined_entrance_animation(self, widget, duration): return None

# --- 莫兰迪主题配色 ---

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

# --- 左栏：竖向时间轴 ---


class TimelineNode(QtWidgets.QWidget):
    clicked = Signal(str)  # name

    def __init__(self, date, hours, title, status, is_last=False):
        super().__init__()
        self.date = date
        self.hours = hours
        self.title = title
        self.status = status  # 'completed', 'current', 'locked'
        self.is_last = is_last
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(100)

        # 获取动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        # 点击粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 闪烁动画 (仅 current)
        self.pulse_val = 0.0
        if self.status == 'current':
            self.pulse_animation = AnimatedValue(0.0)
            self.pulse_animation.valueChanged.connect(self._update_pulse_value)
            self._start_pulse_animation()

    def _start_pulse_animation(self):
        """启动脉冲动画"""
        if hasattr(self, 'pulse_animation'):
            self.pulse_animation.animate_to(
                1.0, 1000, 0, QtCore.QEasingCurve.InOutSine)

            def reverse_pulse():
                self.pulse_animation.animate_to(
                    0.0, 1000, 0, QtCore.QEasingCurve.InOutSine)
                QtCore.QTimer.singleShot(1000, self._start_pulse_animation)

            QtCore.QTimer.singleShot(1000, reverse_pulse)

    def _update_pulse_value(self, value):
        self.pulse_val = value
        self.update()

    def _trigger_click_particles(self):
        """触发点击粒子效果"""
        if hasattr(self, 'particle_system'):
            center = QtCore.QPoint(self.width() // 2, self.height() // 2)
            self.particle_system.create_particle_burst(center, 20)
            self.particle_system.show()
            self.particle_system.trigger_startup_effect(center)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        cx = 30
        cy = 20

        # 主题颜色
        line_color = MorandiTheme.COLOR_BORDER
        accent_color = MorandiTheme.COLOR_CHART_BAR # 亮黄色
        text_primary = MorandiTheme.COLOR_TEXT_NORMAL
        text_secondary = MorandiTheme.COLOR_TEXT_SUBTITLE
        text_disabled = MorandiTheme.COLOR_TEXT_LOCKED

        # 1. 竖线
        if not self.is_last:
            p.setPen(QtGui.QPen(line_color, 2))
            p.drawLine(cx, cy, cx, self.height())

        # 2. 节点圆点
        radius = 10
        if self.status == 'current':
            # 外层脉冲
            pulse_r = radius + 8 * self.pulse_val
            glow_color = QtGui.QColor(accent_color)
            glow_color.setAlpha(int(100 * (1 - self.pulse_val)))

            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(glow_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), pulse_r, pulse_r)

            # 核心
            p.setBrush(accent_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        elif self.status == 'completed':
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(accent_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        else:  # locked
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(text_disabled, 2))
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        # 3. 文字内容
        text_x = 65

        # 标题 (50h / 100h)
        if self.status != 'locked':
            p.setPen(accent_color)
            font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Bold)
            p.setFont(font)
            MorandiTheme.draw_text_at_point_with_shadow(
                p, text_x, cy + 8, self.hours, accent_color)
        else:
            p.setPen(text_disabled)
            font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Bold)
            p.setFont(font)
            p.drawText(text_x, cy + 8, self.hours)

        # 日期
        p.setPen(text_primary)
        font = QtGui.QFont("Segoe UI", 10)
        p.setFont(font)
        fm = QtGui.QFontMetrics(font)
        date_w = fm.horizontalAdvance(self.date)
        MorandiTheme.draw_text_at_point_with_shadow(
            p, self.width() - date_w - 15, cy + 8, self.date, text_primary)

        # 描述
        p.setPen(text_secondary)
        font = QtGui.QFont("Segoe UI", 11)
        p.setFont(font)
        MorandiTheme.draw_text_at_point_with_shadow(
            p, text_x, cy + 28, self.title, text_secondary)

        # 悬停高亮
        if self.hover_progress.value > 0.01:
            bg_color = MorandiTheme.color(MorandiTheme.HEX_BLUE_LIGHT, 25) # 10%
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(bg_color)
            p.drawRoundedRect(5, 5, self.width() - 10, 70, 8, 8)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)

    def mousePressEvent(self, event):
        self._trigger_click_particles()
        if hasattr(self, 'animation_engine'):
            click_anim = self.animation_engine.create_button_press_animation(self)
            if click_anim:
                click_anim.start()

        if self.status == 'completed':
            QtWidgets.QMessageBox.information(
                self, "里程碑回顾", f"查看 {self.hours} 达成时的详细周报...")
        elif self.status == 'locked':
            QtWidgets.QMessageBox.information(
                self, "目标设定", f"设定下个月目标为 {self.hours}？")


class TimelinePanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 数据
        nodes = [
            ("12月1日", "开始记录", "旅程的开始", "completed"),
            ("12月15日", "50h", "渐入佳境", "completed"),
            ("12月31日", "100h", "本月已达成！", "current"),
            ("待解锁", "150h", "下月目标", "locked", True)
        ]

        for date, hours, title, status, *rest in nodes:
            is_last = len(rest) > 0
            node = TimelineNode(date, hours, title, status, is_last)
            layout.addWidget(node)

        layout.addStretch()

# --- 中栏：成长曲线图 (Matplotlib) ---


class GrowthChart(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # 获取动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        self.layout = QtWidgets.QVBoxLayout(self)

        # 设置matplotlib透明背景
        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor='none')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.layout.addWidget(self.canvas)

        self.anim_progress = AnimatedValue(0.0)
        self.anim_progress.valueChanged.connect(self.draw_chart)

        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        self.weeks = ['W1', 'W2', 'W3', 'W4']
        self.weekly_add = [20, 30, 25, 250]
        self.cumulative = [20, 50, 75, 150]

        QtCore.QTimer.singleShot(1500, self.start_anim)

    def start_anim(self):
        self.anim_progress.animate_to(
            1.0, 3000, 0, QtCore.QEasingCurve.OutBack)

        def on_animation_complete():
            center = QtCore.QPoint(self.width() // 2, self.height() // 2)
            self.particle_system.create_particle_burst(center, 30)
            self.particle_system.show()
            self.particle_system.trigger_startup_effect(center)

        QtCore.QTimer.singleShot(3000, on_animation_complete)

    def draw_chart(self, progress):
        self.figure.clear()

        # 莫兰迪配色 (统一主题)
        def to_mpl(qcolor):
            return (qcolor.redF(), qcolor.greenF(), qcolor.blueF(), qcolor.alphaF())

        color_gold = to_mpl(MorandiTheme.COLOR_CHART_BAR)
        color_blue = to_mpl(MorandiTheme.COLOR_BORDER)
        color_text = to_mpl(MorandiTheme.COLOR_TEXT_NORMAL)
        color_grid = to_mpl(MorandiTheme.COLOR_GRID)

        # 双Y轴
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        ax1.set_facecolor('none')
        ax2.set_facecolor('none')

        # 设置样式
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['bottom'].set_color(color_text)
        ax1.spines['left'].set_color(color_text)
        ax1.tick_params(axis='x', colors=color_text, labelsize=10)
        ax1.tick_params(axis='y', colors=color_text, labelsize=10)

        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_color(color_text)
        ax2.tick_params(axis='y', colors=color_gold, labelsize=10)

        x = np.arange(len(self.weeks))

        # 1. 柱状图 (每周新增) - 使用主题色
        bar_heights = [h * progress for h in self.weekly_add]
        # 移除固定 alpha=0.5，改用颜色自身的 alpha (由主题控制)
        bars = ax2.bar(x, bar_heights, color=color_gold,
                       width=0.5, label='每周新增',
                       edgecolor=color_blue, linewidth=1)

        ax2.set_ylim(0, 40)

        # 2. 折线图 (累计) - 莫兰迪蓝
        num_points = len(self.weeks)
        current_idx = progress * (num_points - 1)
        idx_int = int(current_idx)
        idx_frac = current_idx - idx_int

        if progress > 0:
            xs = x[:idx_int+1]
            ys = self.cumulative[:idx_int+1]

            if idx_int < num_points - 1:
                next_x = x[idx_int+1]
                next_y = self.cumulative[idx_int+1]
                curr_x = x[idx_int]
                curr_y = self.cumulative[idx_int]
                interp_x = curr_x + (next_x - curr_x) * idx_frac
                interp_y = curr_y + (next_y - curr_y) * idx_frac
                xs = np.append(xs, interp_x)
                ys = np.append(ys, interp_y)

            ax1.plot(xs, ys, color=color_blue, linewidth=3,
                     marker='o', markersize=6, markerfacecolor=color_blue,
                     markeredgecolor='white', markeredgewidth=1,
                     label='累计时长', alpha=0.9)

            for i, (xi, yi) in enumerate(zip(xs, ys)):
                if i < len(self.cumulative):
                    ax1.annotate(f'{int(self.cumulative[i])}h',
                                 (xi, yi), textcoords="offset points",
                                 xytext=(0, 10), ha='center',
                                 color=color_text, fontsize=9, fontweight='bold')

        ax1.set_ylim(0, 150)
        ax1.set_xticks(x)
        ax1.set_xticklabels(self.weeks, color=color_text,
                            fontsize=11, fontweight='bold')

        ax1.grid(True, alpha=0.1, color=color_text, linestyle='--')

        self.canvas.draw()

# --- 右栏：下月计划 ---


class CheckBoxItem(QtWidgets.QWidget):
    def __init__(self, text, checked=False):
        super().__init__()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setChecked(checked)

        # 莫兰迪复选框
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{ 
                width: 20px; 
                height: 20px; 
                border: 2px solid {MorandiTheme.COLOR_BORDER.name()}; 
                border-radius: 4px;
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{ 
                background-color: {MorandiTheme.COLOR_CHART_BAR.name()}; 
                border-color: {MorandiTheme.COLOR_CHART_BAR.name()};
            }}
            QCheckBox::indicator:hover {{
                border-color: {MorandiTheme.COLOR_CHART_BAR.name()};
            }}
        """)

        label = QtWidgets.QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
            }}
        """)

        layout.addWidget(self.checkbox)
        layout.addWidget(label)
        layout.addStretch()


class NextMonthPlan(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QtWidgets.QLabel("🎯 下月挑战计划")
        title.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_TITLE.name()};
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                margin-bottom: 10px;
            }}
        """)
        self.layout.addWidget(title)

        # 目标进度
        target_box = QtWidgets.QWidget()
        tb_layout = QtWidgets.QVBoxLayout(target_box)
        tb_layout.setContentsMargins(0, 10, 0, 10)

        lbl_target = QtWidgets.QLabel("目标：突破 150 小时")
        lbl_target.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }}
        """)

        # 进度条 - 金色 60%
        progress_bar = QtWidgets.QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(150)
        progress_bar.setValue(100)
        progress_bar.setFixedHeight(12)

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(168, 216, 234, 38);
                border: 1px solid {MorandiTheme.COLOR_BORDER.name()};
                border-radius: 6px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: rgba(255, 215, 0, 250);
                border-radius: 5px;
            }}
        """)

        lbl_curr = QtWidgets.QLabel("当前进度: 100h / 150h (66.7%)")
        lbl_curr.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_SUBTITLE.name()};
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }}
        """)

        tb_layout.addWidget(lbl_target)
        tb_layout.addWidget(progress_bar)
        tb_layout.addWidget(lbl_curr)

        self.layout.addWidget(target_box)

        # 建议策略
        lbl_adv = QtWidgets.QLabel("💡 建议策略:")
        lbl_adv.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_SUBTITLE.name()};
                font-size: 15px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                margin-top: 15px;
                margin-bottom: 10px;
            }}
        """)
        self.layout.addWidget(lbl_adv)

        self.layout.addWidget(CheckBoxItem("保持上午9-11点黄金时段", True))
        self.layout.addWidget(CheckBoxItem("减少下午3点后低效任务", True))
        self.layout.addWidget(CheckBoxItem("周末适当放松 (不设目标)", False))

        self.layout.addStretch()

        # 按钮
        btn = QtWidgets.QPushButton("🚀 生成我的月计划")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFixedHeight(45)

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(168, 216, 234, 30);
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                border: 1px solid rgba(168, 216, 234, 76);
                border-radius: 10px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton:hover {{
                background-color: rgba(168, 216, 234, 64);
                color: #ffd700;
                border-color: rgba(168, 216, 234, 128);
            }}
            QPushButton:pressed {{
                background-color: rgba(168, 216, 234, 100);
            }}
        """)

        btn.clicked.connect(self.generate_plan)
        self.layout.addWidget(btn)

    def generate_plan(self):
        QtWidgets.QMessageBox.information(
            self, "计划生成", "已根据您的策略生成下月日历！\n高效时段已自动标记。")

try:
    from ui.component.visual_enhancements.starry_envelope import ReportEnvelopeContainer
except ImportError:
    try:
        from ..visual_enhancements.starry_envelope import ReportEnvelopeContainer
    except ImportError:
        try:
            from .starry_envelope import ReportEnvelopeContainer
        except ImportError:
            # Fallback for direct execution if path setup worked
            from visual_enhancements.starry_envelope import ReportEnvelopeContainer

# --- 主界面内容 ---


class _MilestoneReportContent(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.resize(1000, 700)
        self.drag_start_pos = None
        
        # 获取动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        # 创建启动粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()
        
        # 初始化星星
        self.stars = self._init_stars()
        self.star_timer = QtCore.QTimer(self)
        self.star_timer.timeout.connect(self.update_stars)
        self.star_timer.start(50)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # 顶部标题 - 金色 100%
        title_lbl = QtWidgets.QLabel("🎉 恭喜！本月专注突破 100 小时！")
        title_lbl.setAlignment(QtCore.Qt.AlignCenter)
        title_lbl.setStyleSheet(f"""
            QLabel {{
                color: #ffd700;
                font-size: 32px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                margin-bottom: 25px;
                padding: 15px;
            }}
        """)

        main_layout.addWidget(title_lbl)

        # 触发启动粒子效果
        QtCore.QTimer.singleShot(500, self._trigger_startup_particles)

        # 中间三栏内容
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(30)

        # 左栏：时间轴
        left_box = QtWidgets.QGroupBox("📈 成长足迹")
        self._apply_groupbox_style(left_box)
        lb_layout = QtWidgets.QVBoxLayout(left_box)
        lb_layout.addWidget(TimelinePanel())
        content_layout.addWidget(left_box, 1)

        # 中栏：曲线图
        mid_box = QtWidgets.QGroupBox("📊 成长曲线")
        self._apply_groupbox_style(mid_box)
        mb_layout = QtWidgets.QVBoxLayout(mid_box)
        mb_layout.addWidget(GrowthChart())
        content_layout.addWidget(mid_box, 2)

        # 右栏：计划
        right_box = QtWidgets.QGroupBox("🎯 下月规划")
        self._apply_groupbox_style(right_box)
        rb_layout = QtWidgets.QVBoxLayout(right_box)
        rb_layout.addWidget(NextMonthPlan())
        content_layout.addWidget(right_box, 1)

        main_layout.addLayout(content_layout)

        # 底部预测条
        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setFixedHeight(40)
        bb_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(0, 0, 0, 0)

        lbl_pred = QtWidgets.QLabel("🚀 预测：按此趋势，下月有望达到 135 小时！")
        lbl_pred.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                padding: 8px 15px;
                background: rgba(168, 216, 234, 30);
                border-radius: 8px;
            }}
        """)
        bb_layout.addWidget(lbl_pred)
        bb_layout.addStretch()

        # 关闭按钮
        close_btn = QtWidgets.QPushButton("✕ 关闭")
        close_btn.setFixedSize(100, 35)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(168, 216, 234, 180);
                color: #1a1a1a;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #ffd700;
                color: #1a1a1a;
            }}
        """)
        # 连接关闭按钮
        close_btn.clicked.connect(lambda: self.window().close()) # 关闭父窗口
        bb_layout.addWidget(close_btn)

        main_layout.addWidget(bottom_bar)
        
        # 确保所有子控件都已显示（避免渲染延迟）
        # 强制设置透明度为1，避免被动画引擎误设为0
        self.setWindowOpacity(1.0)
        left_box.setWindowOpacity(1.0)
        mid_box.setWindowOpacity(1.0)
        right_box.setWindowOpacity(1.0)

        close_btn.clicked.connect(self.close)
        bb_layout.addWidget(close_btn)

        main_layout.addWidget(bottom_bar)
        
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
        
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect()
        
        # 背景：径向渐变
        gradient = QtGui.QRadialGradient(rect.center(), max(rect.width(), rect.height()) / 1.2)
        gradient.setColorAt(0, MorandiTheme.COLOR_BG_CENTER)
        gradient.setColorAt(1, MorandiTheme.COLOR_BG_EDGE)
        
        p.setBrush(gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(rect, 12, 12)
        
        # 绘制星星
        for star in self.stars:
            c = QtGui.QColor("#ffd700")
            c.setAlpha(int(star['alpha']))
            p.setBrush(c)
            p.drawEllipse(QtCore.QPointF(star['x'], star['y']), star['size'], star['size'])
            
        # 边框 (30%透明)
        p.setPen(QtGui.QPen(MorandiTheme.COLOR_BORDER, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12, 12)
        
        # 内阴影
        inner_pen = QtGui.QPen(QtGui.QColor(168, 216, 234, 12), 4)
        p.setPen(inner_pen)
        p.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 10, 10)

    def _apply_groupbox_style(self, groupbox):
        """应用GroupBox的主题样式"""
        border_c = MorandiTheme.COLOR_BORDER.name()
        text_c = MorandiTheme.COLOR_TEXT_NORMAL.name()
        title_c = MorandiTheme.COLOR_TEXT_TITLE.name()
        
        # 使用简单的字符串拼接，避免任何格式化歧义
        style = (
            "QGroupBox {"
            "    color: " + text_c + ";"
            "    background-color: transparent;"
            "    border: 2px solid " + border_c + ";"
            "    border-radius: 15px;"
            "    margin-top: 15px;"
            "    font-weight: bold;"
            "    font-size: 14px;"
            "    padding-top: 10px;"
            "}"
            "QGroupBox::title {"
            "    subcontrol-origin: margin;"
            "    left: 15px;"
            "    padding: 0px 8px 0px 8px;"
            "    color: " + title_c + ";"
            "    font-size: 16px;"
            "    font-weight: bold;"
            "}"
        )
        groupbox.setStyleSheet(style)

    def _trigger_startup_particles(self):
        """触发启动粒子效果"""
        if hasattr(self, 'particle_system'):
            center = QtCore.QPoint(self.width() // 2, 100)  # 在标题附近
            self.particle_system.create_particle_burst(center, 40)
            self.particle_system.show()
            self.particle_system.trigger_startup_effect(center)

    def showEvent(self, event):
        """窗口显示时的事件"""
        super().showEvent(event)
        # 禁用淡入动画，直接显示
        # 创建入场动画
        # if hasattr(self, 'animation_engine'):
        #     entrance_anim = self.animation_engine.create_combined_entrance_animation(
        #         self, 800)
        #     if entrance_anim:
        #         entrance_anim.start()
        
        # 确保所有内容立即可见
        self.update()


class MilestoneReport(ReportEnvelopeContainer):
    clicked = Signal()

    def __init__(self):
        super().__init__(expanded_height=700)
        self.resize(1000, 280)
        self.drag_start_pos = None

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.content = _MilestoneReportContent()
        self.set_content(self.content)
        
        # 初始状态：完全居中显示（不偏移）
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            center_point = screen.geometry().center()
            # 居中，不加偏移
            target_pos = center_point - self.rect().center()
            self.move(target_pos)
            
        # 连接折叠状态改变信号，实现动态移动
        self.stateChanged.connect(self._on_collapse_state_changed)

    def _on_collapse_state_changed(self, is_expanded: bool):
        """折叠状态改变时调整窗口位置"""
        screen = QtGui.QGuiApplication.primaryScreen()
        if not screen:
            return
            
        screen_center = screen.geometry().center()
        
        if is_expanded:
            # 展开时：向上偏移 200px
            # 目标位置：屏幕中心 - 窗口中心(展开后) - 偏移量
            target_pos = screen_center - QtCore.QPoint(self.width() // 2, self.height() // 2) - QtCore.QPoint(0, 200)
            
            # 使用动画平滑移动窗口
            self.pos_anim = QtCore.QPropertyAnimation(self, b"pos")
            self.pos_anim.setDuration(300)
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(target_pos)
            self.pos_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            self.pos_anim.start()
            
        else:
            # 折叠（收起）时：回到屏幕正中央
            # 目标位置：屏幕中心 - 信封中心
            # 重新计算居中位置（基于当前信封大小）
            # 注意：此时 self.height() 已经在动画中变化，我们使用 collapsed_height 来计算目标位置
            
            # 我们希望信封始终在屏幕正中央
            target_pos = screen_center - QtCore.QPoint(self.width() // 2, self.collapsed_height // 2)
            
            self.pos_anim = QtCore.QPropertyAnimation(self, b"pos")
            self.pos_anim.setDuration(300)
            self.pos_anim.setStartValue(self.pos())
            self.pos_anim.setEndValue(target_pos)
            self.pos_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            self.pos_anim.start()

    def changeEvent(self, event):
        """处理窗口状态变化"""
        if event.type() == QtCore.QEvent.ActivationChange:
            # 如果失去焦点，关闭窗口
            if not self.isActiveWindow():
                self.close()
        super().changeEvent(event)

    def mousePressEvent(self, event):
        # 允许拖动
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


def show_milestone_report():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)

    # 启用高 DPI
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.AA_EnableHighDpiScaling, True)

    window = MilestoneReport()
    window.show()

    if not QtWidgets.QApplication.instance():
        sys.exit(app.exec())
    else:
        app.exec()


if __name__ == "__main__":
    show_milestone_report()
