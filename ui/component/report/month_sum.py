from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
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
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(current_dir)))

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
            print(
                "Warning: Could not import visual enhancement components. Using placeholders.")

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
                def create_combined_entrance_animation(
                    self, widget, duration): return None

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

# --- 月计划日历数据模型和工具函数 ---


@dataclass
class DayData:
    """单日数据"""
    day: int          # 日期 (1-31)
    hours: float      # 专注时长
    weekday: int      # 星期几 (0=周一, 6=周日)
    is_weekend: bool  # 是否周末


@dataclass
class MonthPlanData:
    """月计划数据"""
    month: int                    # 月份 (1)
    year: int                     # 年份 (2025)
    target_hours: int             # 目标总时长 (150)
    days: List[DayData]           # 每日数据
    encouragement: str            # 鼓励语

    def get_current_total(self) -> float:
        """计算当前总时长"""
        return sum(day.hours for day in self.days)

    def get_completion_rate(self) -> float:
        """计算完成率"""
        return self.get_current_total() / self.target_hours if self.target_hours > 0 else 0.0


def format_hours(hours: float) -> str:
    """格式化时长显示

    Args:
        hours: 时长（小时）

    Returns:
        格式化的字符串，例如 "5.0h" 或 "5.5h"
    """
    if hours == int(hours):
        return f"{int(hours)}h"
    else:
        return f"{hours:.1f}h"


def distribute_hours_to_days(total: int, num_days: int, year: int = 2025, month: int = 1) -> List[float]:
    """将总时长分配到各天

    Args:
        total: 总时长（150）
        num_days: 天数（31）
        year: 年份
        month: 月份

    Returns:
        长度为num_days的列表，每个元素代表该天的时长
    """
    # 计算每天是星期几
    base_date = datetime(year, month, 1)
    weekdays = [(base_date + timedelta(days=i)).weekday()
                for i in range(num_days)]

    # 初始化每天的时长
    hours_list = []

    # 工作日分配较多时长（5-6小时），周末较少（3-4小时）
    for weekday in weekdays:
        if weekday < 5:  # 周一到周五
            base_hours = 5.5
            variation = random.uniform(-0.5, 0.5)
        else:  # 周末
            base_hours = 3.5
            variation = random.uniform(-0.5, 0.5)

        hours_list.append(max(0, base_hours + variation))

    # 调整总和使其精确等于目标值
    current_total = sum(hours_list)
    if current_total > 0:
        adjustment_factor = total / current_total
        hours_list = [h * adjustment_factor for h in hours_list]

    # 四舍五入到一位小数
    hours_list = [round(h, 1) for h in hours_list]

    # 最后微调确保总和精确
    final_total = sum(hours_list)
    diff = total - final_total
    if abs(diff) > 0.01:
        # 将差值加到第一个非零元素上
        for i in range(len(hours_list)):
            if hours_list[i] > 0:
                hours_list[i] = round(hours_list[i] + diff, 1)
                break

    return hours_list

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
        accent_color = MorandiTheme.COLOR_CHART_BAR  # 亮黄色
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
            bg_color = MorandiTheme.color(
                MorandiTheme.HEX_BLUE_LIGHT, 25)  # 10%
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
            click_anim = self.animation_engine.create_button_press_animation(
                self)
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
        ax2.spines['right'].set_visible(False)  # 隐藏右侧轴线
        ax2.set_yticks([])  # 隐藏右侧刻度和标签

        x = np.arange(len(self.weeks))

        # 1. 柱状图 (每周新增) - 使用主题色
        bar_heights = [h * progress for h in self.weekly_add]
        # 移除固定 alpha=0.5，改用颜色自身的 alpha (由主题控制)
        bars = ax2.bar(x, bar_heights, color=color_gold,
                       width=0.5, label='每周新增',
                       edgecolor=color_blue, linewidth=1)
        
        # 在柱状图上方添加数值标签
        for rect, h_val in zip(bars, bar_heights):
            height = rect.get_height()
            if height > 1:  # 只有高度大于1才显示
                ax2.text(rect.get_x() + rect.get_width()/2., height + 0.5,
                         f'{int(h_val)}h',
                         ha='center', va='bottom', 
                         color=color_gold, fontsize=10, fontweight='bold')

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
                                 color=color_gold, fontsize=9, fontweight='bold')

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

# --- 月计划日历弹窗组件 ---


class DayCell(QtWidgets.QWidget):
    """单个日期单元格"""
    valueChanged = Signal(int, float)  # (day, hours)

    def __init__(self, day: int, hours: float = 0.0, parent=None):
        super().__init__(parent)
        self.day = day
        self._hours = hours
        self._task = ""  # 每日任务
        self.setFixedSize(100, 95)  # 紧凑的高度
        self.setCursor(QtCore.Qt.PointingHandCursor)

        # 悬停动画
        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        # 布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)  # 减小边距
        layout.setSpacing(2)  # 减小间距

        # 日期标签
        self.day_label = QtWidgets.QLabel(f"{day}日")
        self.day_label.setAlignment(QtCore.Qt.AlignCenter)
        self.day_label.setFixedHeight(16)  # 固定高度
        self.day_label.setStyleSheet("""
            QLabel {
                color: rgba(168, 216, 234, 204);  /* 莫兰迪蓝 80%透明度 */
                font-size: 10px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                background: transparent;
            }
        """)
        layout.addWidget(self.day_label)

        # 时长输入框
        self.spin_box = QtWidgets.QDoubleSpinBox()
        self.spin_box.setMinimum(0.0)
        self.spin_box.setMaximum(24.0)
        self.spin_box.setSingleStep(0.5)
        self.spin_box.setDecimals(1)
        self.spin_box.setValue(hours)
        self.spin_box.setSuffix("h")
        self.spin_box.setAlignment(QtCore.Qt.AlignCenter)
        self.spin_box.setFixedHeight(26)  # 减小高度
        self.spin_box.setStyleSheet("""
            QDoubleSpinBox {
                color: rgba(255, 215, 0, 255);  /* 金色 100%透明度 */
                background: rgba(168, 216, 234, 20);  /* 莫兰迪蓝 8%透明度 */
                border: 1px solid rgba(168, 216, 234, 76);  /* 莫兰迪蓝 30%透明度 */
                border-radius: 4px;
                padding: 3px;
                font-size: 13px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QDoubleSpinBox:hover {
                border-color: rgba(255, 215, 0, 255);  /* 金色边框 */
                background: rgba(168, 216, 234, 38);  /* 莫兰迪蓝 15%透明度 */
            }
            QDoubleSpinBox:focus {
                border: 2px solid rgba(255, 215, 0, 255);  /* 金色边框 */
                background: rgba(168, 216, 234, 38);  /* 莫兰迪蓝 15%透明度 */
            }
        """)

        self.spin_box.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.spin_box)

        # 任务文本框
        self.task_input = QtWidgets.QLineEdit()
        self.task_input.setPlaceholderText("任务...")
        self.task_input.setAlignment(QtCore.Qt.AlignCenter)
        self.task_input.setFixedHeight(24)  # 减小高度
        self.task_input.setStyleSheet("""
            QLineEdit {
                color: rgba(168, 216, 234, 230);  /* 莫兰迪蓝 90%透明度 */
                background: rgba(168, 216, 234, 15);  /* 莫兰迪蓝 6%透明度 */
                border: 1px solid rgba(168, 216, 234, 76);  /* 莫兰迪蓝 30%透明度 */
                border-radius: 4px;
                padding: 3px;
                font-size: 10px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit::placeholder {
                color: rgba(168, 216, 234, 128);  /* 莫兰迪蓝 50%透明度 */
            }
            QLineEdit:hover {
                border-color: rgba(168, 216, 234, 128);  /* 莫兰迪蓝 50%透明度 */
                background: rgba(168, 216, 234, 25);  /* 莫兰迪蓝 10%透明度 */
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 215, 0, 200);  /* 金色边框 */
                background: rgba(168, 216, 234, 30);  /* 莫兰迪蓝 12%透明度 */
            }
        """)
        self.task_input.textChanged.connect(self._on_task_changed)
        layout.addWidget(self.task_input)

        # 移除 addStretch() 以消除多余空白

    def _on_value_changed(self, value):
        """时长值改变时触发"""
        self._hours = value
        self.valueChanged.emit(self.day, value)

    def _on_task_changed(self, text):
        """任务文本改变时触发"""
        self._task = text

    def set_hours(self, hours: float):
        """设置时长"""
        self._hours = hours
        self.spin_box.blockSignals(True)
        self.spin_box.setValue(hours)
        self.spin_box.blockSignals(False)

    def get_hours(self) -> float:
        """获取时长"""
        return self._hours

    def set_task(self, task: str):
        """设置任务"""
        self._task = task
        self.task_input.blockSignals(True)
        self.task_input.setText(task)
        self.task_input.blockSignals(False)

    def get_task(self) -> str:
        """获取任务"""
        return self._task

    def paintEvent(self, event):
        """自定义绘制"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()

        # 背景 - 8%-15%透明度
        base_alpha = 20  # 8%透明度
        hover_alpha = 38  # 15%透明度
        alpha = int(base_alpha + (hover_alpha - base_alpha)
                    * self.hover_progress.value)
        bg_color = QtGui.QColor(168, 216, 234, alpha)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg_color)
        p.drawRoundedRect(rect, 8, 8)

        # 边框 - 30%透明度
        border_color = QtGui.QColor(168, 216, 234, 76)  # 30%透明度
        p.setPen(QtGui.QPen(border_color, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)

    def enterEvent(self, event):
        """鼠标进入"""
        self.hover_progress.animate_to(1.0, 200)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开"""
        self.hover_progress.animate_to(0.0, 200)
        super().leaveEvent(event)


class MonthlyPlanDialog(QtWidgets.QDialog):
    """月计划日历弹窗"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_hours = 150
        self.day_cells = []

        # 设置窗口属性
        self.setWindowTitle("1月专注计划")
        self.setFixedSize(800, 750)  # 紧凑的高度
        self.setModal(True)

        # 设置窗口透明属性，使背景可以透出下层页面
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        # 初始化装饰星星
        self._init_stars()

        # 初始化UI
        self._init_ui()

        # 分配时长
        self._distribute_hours()

    def _init_stars(self):
        """初始化装饰星星"""
        self.stars = []
        # 创建8颗装饰星星
        for _ in range(8):
            self.stars.append({
                'x': random.randint(50, 750),
                'y': random.randint(50, 650),
                'size': random.uniform(2, 4),
                'delay': random.random() * 3,
                'alpha': 204  # 80%透明度
            })

        # 启动星星闪烁动画定时器
        self.star_timer = QtCore.QTimer(self)
        self.star_timer.timeout.connect(self._update_stars)
        self.star_timer.start(50)

    def _update_stars(self):
        """更新星星闪烁动画"""
        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay() / 1000.0
        for star in self.stars:
            # 3秒周期闪烁
            t = (current_time + star['delay']) % 3.0
            norm = t / 1.5 if t < 1.5 else (3.0 - t) / 1.5
            # 在50%-80%透明度之间闪烁
            star['alpha'] = int(128 + (76 * norm))
        self.update()

    def _init_ui(self):
        """构建UI布局"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 鼓励语列表
        encouragements = [
            "🌟 新的一月，新的开始！让我们一起创造专注的奇迹！",
            "💪 150小时的目标在等待，每一天都是新的机会！",
            "🎯 专注成就卓越，坚持铸就辉煌！",
            "✨ 相信自己，你可以完成这个挑战！",
            "🚀 一步一个脚印，向着目标前进！"
        ]

        # 标题
        title_label = QtWidgets.QLabel(random.choice(encouragements))
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 215, 0, 255);  /* 金色 100%透明度 */
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                padding: 10px;
                background: transparent;
            }
        """)
        main_layout.addWidget(title_label)

        # 日历网格容器
        calendar_widget = QtWidgets.QWidget()
        calendar_layout = QtWidgets.QGridLayout(calendar_widget)
        calendar_layout.setSpacing(10)

        # 星期标题
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for col, weekday in enumerate(weekdays):
            label = QtWidgets.QLabel(weekday)
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 215, 0, 255);  /* 金色 100%透明度 */
                    font-size: 14px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                    background: transparent;
                }
            """)
            calendar_layout.addWidget(label, 0, col)

        # 创建31个日期单元格
        # 2025年1月1日是周三（weekday=2）
        start_weekday = 2  # 周三

        for day in range(1, 32):
            cell = DayCell(day, 0.0, self)
            cell.valueChanged.connect(self._on_day_value_changed)
            self.day_cells.append(cell)

            # 计算位置
            position = start_weekday + day - 1
            row = position // 7 + 1  # +1 因为第0行是星期标题
            col = position % 7

            calendar_layout.addWidget(cell, row, col)

        main_layout.addWidget(calendar_widget)

        # 总时长显示
        self.total_label = QtWidgets.QLabel(
            f"总计: 0.0h / {self.target_hours}h (0.0%)")
        self.total_label.setAlignment(QtCore.Qt.AlignCenter)
        self.total_label.setStyleSheet("""
            QLabel {
                color: rgba(168, 216, 234, 255);  /* 莫兰迪蓝 100%透明度 */
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                padding: 10px;
                background: rgba(168, 216, 234, 20);  /* 莫兰迪蓝 8%透明度 */
                border: 1px solid rgba(168, 216, 234, 76);  /* 莫兰迪蓝 30%透明度 */
                border-radius: 8px;
            }
        """)
        main_layout.addWidget(self.total_label)

        # 关闭按钮
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        close_btn = QtWidgets.QPushButton("✕ 关闭")
        close_btn.setFixedSize(120, 40)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(168, 216, 234, 38);  /* 莫兰迪蓝 15%透明度 */
                color: rgba(168, 216, 234, 255);  /* 莫兰迪蓝 100%透明度 */
                border: 1px solid rgba(168, 216, 234, 76);  /* 莫兰迪蓝 30%透明度 */
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 215, 0, 38);  /* 金色 15%透明度 */
                color: rgba(255, 215, 0, 255);  /* 金色 100%透明度 */
                border-color: rgba(255, 215, 0, 76);  /* 金色 30%透明度 */
            }
            QPushButton:pressed {
                background-color: rgba(168, 216, 234, 51);  /* 莫兰迪蓝 20%透明度 */
            }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        main_layout.addLayout(button_layout)

    def _distribute_hours(self):
        """分配150小时到31天"""
        hours_list = distribute_hours_to_days(self.target_hours, 31, 2025, 1)

        for i, hours in enumerate(hours_list):
            if i < len(self.day_cells):
                self.day_cells[i].set_hours(hours)

        self._update_total_display()

    def _on_day_value_changed(self, day: int, hours: float):
        """处理日期时长变化"""
        self._update_total_display()

    def _update_total_display(self):
        """更新总时长显示"""
        current_total = sum(cell.get_hours() for cell in self.day_cells)
        completion_rate = (current_total / self.target_hours *
                           100) if self.target_hours > 0 else 0

        self.total_label.setText(
            f"总计: {current_total:.1f}h / {self.target_hours}h ({completion_rate:.1f}%)"
        )

    def get_current_total(self) -> float:
        """获取当前总时长"""
        return sum(cell.get_hours() for cell in self.day_cells)

    def _trigger_opening_particles(self):
        """触发开场粒子效果"""
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.particle_system.create_particle_burst(center, 30)
        self.particle_system.show()
        self.particle_system.trigger_startup_effect(center)

    def showEvent(self, event):
        """窗口显示时触发"""
        super().showEvent(event)
        # 延迟触发粒子效果
        QtCore.QTimer.singleShot(200, self._trigger_opening_particles)

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == QtCore.Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """自定义绘制背景"""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect()

        # 背景渐变 - 使用莫兰迪蓝的渐变 (几乎完全透明)
        gradient = QtGui.QRadialGradient(
            rect.center(), max(rect.width(), rect.height()) / 1.2)
        # 中心：莫兰迪蓝 2%透明度 (几乎完全透明)
        gradient.setColorAt(0, QtGui.QColor(168, 216, 234, 5))
        # 边缘：莫兰迪蓝 2%透明度 (几乎完全透明)
        gradient.setColorAt(1, QtGui.QColor(168, 216, 234, 5))

        p.setBrush(gradient)
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(rect, 12, 12)

        # 绘制装饰星星 - 莫兰迪蓝 80%透明度闪烁
        for star in self.stars:
            star_color = QtGui.QColor(168, 216, 234, star['alpha'])
            p.setBrush(star_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(QtCore.QPointF(
                star['x'], star['y']), star['size'], star['size'])

        # 边框 - 莫兰迪蓝 30%透明度
        border_color = QtGui.QColor(168, 216, 234, 76)
        p.setPen(QtGui.QPen(border_color, 2))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 12, 12)


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
        """生成月计划 - 显示月历弹窗"""
        dialog = MonthlyPlanDialog(self)
        dialog.exec()


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

# --- 画卷展开动画组件 ---


class ExpandCollapseButton(QtWidgets.QPushButton):
    """展开/折叠按钮"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(35)
        self.set_expanded_state(False)
        self._apply_morandi_style()

    def set_expanded_state(self, is_expanded: bool):
        """设置按钮状态（更新图标和文本）"""
        self.is_expanded = is_expanded
        if is_expanded:
            self.setText("⇇ 收起")
            self.setToolTip("收起左右栏")
        else:
            self.setText("⇄ 展开查看更多")
            self.setToolTip("展开查看完整内容")

    def _apply_morandi_style(self):
        """应用莫兰迪主题样式"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(168, 216, 234, 30);
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                border: 1px solid rgba(168, 216, 234, 76);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
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


class ColumnContainer(QtWidgets.QWidget):
    """栏容器，支持滑动和透明度动画"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.content_widget = None
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def set_content(self, widget: QtWidgets.QWidget):
        """设置容器内容"""
        if self.content_widget:
            self.layout.removeWidget(self.content_widget)
        self.content_widget = widget
        self.layout.addWidget(widget)


class ScrollableThreeColumnLayout(QtWidgets.QWidget):
    """可滚动的三栏布局"""

    expansionStateChanged = Signal(bool)  # True=展开, False=折叠

    def __init__(self, parent=None):
        super().__init__(parent)

        # 动画状态
        self.is_expanded = False
        self.is_animating = False

        # 动画引擎和粒子系统
        self.animation_engine = PrecisionAnimationEngine(self)
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 创建三个栏容器
        self.left_column = ColumnContainer(self)
        self.middle_column = ColumnContainer(self)
        self.right_column = ColumnContainer(self)

        # 设置初始几何形状（折叠状态）
        # 注意：初始时中栏应该占据整个宽度
        self.left_column.setGeometry(-250, 0, 250, self.height())
        self.middle_column.setGeometry(0, 0, self.width(), self.height())
        self.right_column.setGeometry(self.width(), 0, 250, self.height())

        # 初始隐藏左右栏
        self.left_column.hide()
        self.right_column.hide()

        # 设置左右栏初始透明度为0
        left_opacity = QtWidgets.QGraphicsOpacityEffect()
        left_opacity.setOpacity(0.0)
        self.left_column.setGraphicsEffect(left_opacity)

        right_opacity = QtWidgets.QGraphicsOpacityEffect()
        right_opacity.setOpacity(0.0)
        self.right_column.setGraphicsEffect(right_opacity)

    def set_left_widget(self, widget: QtWidgets.QWidget):
        """设置左栏内容"""
        self.left_column.set_content(widget)

    def set_middle_widget(self, widget: QtWidgets.QWidget):
        """设置中栏内容"""
        self.middle_column.set_content(widget)

    def set_right_widget(self, widget: QtWidgets.QWidget):
        """设置右栏内容"""
        self.right_column.set_content(widget)

    def toggle(self):
        """切换展开/折叠状态"""
        if self.is_animating:
            return  # 忽略点击，防止动画冲突

        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """展开左右栏（触发动画）"""
        if not self.left_column or not self.right_column:
            print("Warning: Columns not initialized")
            return

        if self.is_animating:
            return

        self.is_animating = True

        # 显示左右栏
        self.left_column.show()
        self.right_column.show()

        # 创建动画组
        anim_group = QtCore.QParallelAnimationGroup(self)

        # 左栏滑入动画
        left_pos_anim = QtCore.QPropertyAnimation(
            self.left_column, b"geometry")
        left_pos_anim.setDuration(700)
        left_pos_anim.setStartValue(QtCore.QRect(-250, 0, 250, self.height()))
        left_pos_anim.setEndValue(QtCore.QRect(0, 0, 250, self.height()))
        left_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(left_pos_anim)

        # 左栏透明度动画
        left_opacity_effect = self.left_column.graphicsEffect()
        if not isinstance(left_opacity_effect, QtWidgets.QGraphicsOpacityEffect):
            left_opacity_effect = QtWidgets.QGraphicsOpacityEffect()
            self.left_column.setGraphicsEffect(left_opacity_effect)
        left_opacity_anim = QtCore.QPropertyAnimation(
            left_opacity_effect, b"opacity")
        left_opacity_anim.setDuration(700)
        left_opacity_anim.setStartValue(0.0)
        left_opacity_anim.setEndValue(1.0)
        left_opacity_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        anim_group.addAnimation(left_opacity_anim)

        # 右栏滑入动画
        total_width = self.width()
        middle_width = total_width - 500
        right_pos_anim = QtCore.QPropertyAnimation(
            self.right_column, b"geometry")
        right_pos_anim.setDuration(700)
        right_pos_anim.setStartValue(QtCore.QRect(
            total_width, 0, 250, self.height()))
        right_pos_anim.setEndValue(QtCore.QRect(
            250 + middle_width, 0, 250, self.height()))
        right_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(right_pos_anim)

        # 右栏透明度动画
        right_opacity_effect = self.right_column.graphicsEffect()
        if not isinstance(right_opacity_effect, QtWidgets.QGraphicsOpacityEffect):
            right_opacity_effect = QtWidgets.QGraphicsOpacityEffect()
            self.right_column.setGraphicsEffect(right_opacity_effect)
        right_opacity_anim = QtCore.QPropertyAnimation(
            right_opacity_effect, b"opacity")
        right_opacity_anim.setDuration(700)
        right_opacity_anim.setStartValue(0.0)
        right_opacity_anim.setEndValue(1.0)
        right_opacity_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        anim_group.addAnimation(right_opacity_anim)

        # 中栏位置调整
        total_width = self.width()
        middle_width = total_width - 500  # 减去左右栏的宽度
        middle_pos_anim = QtCore.QPropertyAnimation(
            self.middle_column, b"geometry")
        middle_pos_anim.setDuration(700)
        middle_pos_anim.setStartValue(
            QtCore.QRect(0, 0, total_width, self.height()))
        middle_pos_anim.setEndValue(QtCore.QRect(
            250, 0, middle_width, self.height()))
        middle_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(middle_pos_anim)

        # 动画完成回调
        def on_animation_finished():
            self.is_animating = False
            self.is_expanded = True
            self._trigger_completion_particles()
            self.expansionStateChanged.emit(True)

        anim_group.finished.connect(on_animation_finished)

        # 延迟触发粒子拖尾
        QtCore.QTimer.singleShot(50, self._trigger_trail_particles)

        # 启动动画
        anim_group.start()

    def collapse(self):
        """折叠左右栏（触发动画）"""
        if not self.left_column or not self.right_column:
            print("Warning: Columns not initialized")
            return

        if self.is_animating:
            return

        self.is_animating = True

        # 创建动画组
        anim_group = QtCore.QParallelAnimationGroup(self)

        # 左栏滑出动画
        left_pos_anim = QtCore.QPropertyAnimation(
            self.left_column, b"geometry")
        left_pos_anim.setDuration(700)
        left_pos_anim.setStartValue(QtCore.QRect(0, 0, 250, self.height()))
        left_pos_anim.setEndValue(QtCore.QRect(-250, 0, 250, self.height()))
        left_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(left_pos_anim)

        # 左栏透明度动画
        left_opacity_effect = self.left_column.graphicsEffect()
        if isinstance(left_opacity_effect, QtWidgets.QGraphicsOpacityEffect):
            left_opacity_anim = QtCore.QPropertyAnimation(
                left_opacity_effect, b"opacity")
            left_opacity_anim.setDuration(700)
            left_opacity_anim.setStartValue(1.0)
            left_opacity_anim.setEndValue(0.0)
            left_opacity_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            anim_group.addAnimation(left_opacity_anim)

        # 右栏滑出动画
        total_width = self.width()
        middle_width = total_width - 500
        right_pos_anim = QtCore.QPropertyAnimation(
            self.right_column, b"geometry")
        right_pos_anim.setDuration(700)
        right_pos_anim.setStartValue(QtCore.QRect(
            250 + middle_width, 0, 250, self.height()))
        right_pos_anim.setEndValue(QtCore.QRect(
            total_width, 0, 250, self.height()))
        right_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(right_pos_anim)

        # 右栏透明度动画
        right_opacity_effect = self.right_column.graphicsEffect()
        if isinstance(right_opacity_effect, QtWidgets.QGraphicsOpacityEffect):
            right_opacity_anim = QtCore.QPropertyAnimation(
                right_opacity_effect, b"opacity")
            right_opacity_anim.setDuration(700)
            right_opacity_anim.setStartValue(1.0)
            right_opacity_anim.setEndValue(0.0)
            right_opacity_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
            anim_group.addAnimation(right_opacity_anim)

        # 中栏位置恢复
        total_width = self.width()
        middle_width = total_width - 500
        middle_pos_anim = QtCore.QPropertyAnimation(
            self.middle_column, b"geometry")
        middle_pos_anim.setDuration(700)
        middle_pos_anim.setStartValue(QtCore.QRect(
            250, 0, middle_width, self.height()))
        middle_pos_anim.setEndValue(
            QtCore.QRect(0, 0, total_width, self.height()))
        middle_pos_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        anim_group.addAnimation(middle_pos_anim)

        # 动画完成回调
        def on_animation_finished():
            self.is_animating = False
            self.is_expanded = False
            self.left_column.hide()
            self.right_column.hide()
            self.expansionStateChanged.emit(False)

        anim_group.finished.connect(on_animation_finished)

        # 启动动画
        anim_group.start()

    def _trigger_trail_particles(self):
        """触发拖尾粒子效果"""
        # 左侧拖尾
        left_center = QtCore.QPoint(125, self.height() // 2)
        self.particle_system.create_particle_burst(left_center, 15)

        # 右侧拖尾
        right_center = QtCore.QPoint(875, self.height() // 2)
        self.particle_system.create_particle_burst(right_center, 15)

        self.particle_system.show()

    def _trigger_completion_particles(self):
        """触发完成粒子爆发"""
        # 左栏爆发
        left_center = QtCore.QPoint(125, self.height() // 2)
        self.particle_system.create_particle_burst(left_center, 20)

        # 右栏爆发
        right_center = QtCore.QPoint(875, self.height() // 2)
        self.particle_system.create_particle_burst(right_center, 20)

        self.particle_system.trigger_startup_effect(left_center)

    def resizeEvent(self, event):
        """窗口大小改变时调整布局"""
        super().resizeEvent(event)
        if not self.is_animating:
            total_width = self.width()
            if self.is_expanded:
                # 展开状态：左250 + 中(剩余-500) + 右250
                middle_width = total_width - 500
                self.left_column.setGeometry(0, 0, 250, self.height())
                self.middle_column.setGeometry(
                    250, 0, middle_width, self.height())
                self.right_column.setGeometry(
                    250 + middle_width, 0, 250, self.height())
            else:
                # 折叠状态：中栏占据全部宽度
                self.left_column.setGeometry(-250, 0, 250, self.height())
                self.middle_column.setGeometry(
                    0, 0, total_width, self.height())
                self.right_column.setGeometry(
                    total_width, 0, 250, self.height())

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
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

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

        # 创建可滚动三栏布局
        self.three_column_layout = ScrollableThreeColumnLayout(self)
        self.three_column_layout.setFixedHeight(550)  # 设置固定高度，减小以适应窗口

        # 左栏：时间轴
        left_box = QtWidgets.QGroupBox("📈 成长足迹")
        self._apply_groupbox_style(left_box)
        lb_layout = QtWidgets.QVBoxLayout(left_box)
        lb_layout.addWidget(TimelinePanel())
        self.three_column_layout.set_left_widget(left_box)

        # 中栏：曲线图（可点击展开/折叠）
        mid_box = QtWidgets.QGroupBox("📊 成长曲线 (点击展开/折叠)")
        self._apply_groupbox_style(mid_box)
        mid_box.setCursor(QtCore.Qt.PointingHandCursor)
        mid_box.mousePressEvent = lambda event: self.three_column_layout.toggle()
        mb_layout = QtWidgets.QVBoxLayout(mid_box)
        mb_layout.addWidget(GrowthChart())

        self.three_column_layout.set_middle_widget(mid_box)

        # 右栏：计划
        right_box = QtWidgets.QGroupBox("🎯 下月规划")
        self._apply_groupbox_style(right_box)
        rb_layout = QtWidgets.QVBoxLayout(right_box)
        rb_layout.addWidget(NextMonthPlan())
        self.three_column_layout.set_right_widget(right_box)

        main_layout.addWidget(self.three_column_layout)

        # 底部栏：预测条 + 关闭按钮
        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setFixedHeight(40)
        bb_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(0, 0, 0, 0)
        bb_layout.setSpacing(15)

        # 预测标签（左侧）
        lbl_pred = QtWidgets.QLabel("🚀 预测：按此趋势，\n下月有望达到 135 小时！")
        lbl_pred.setWordWrap(True)  # 启用自动换行
        lbl_pred.setStyleSheet(f"""
            QLabel {{
                color: {MorandiTheme.COLOR_TEXT_NORMAL.name()};
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                padding: 6px 12px;
                background: rgba(168, 216, 234, 30);
                border-radius: 8px;
            }}
        """)
        bb_layout.addWidget(lbl_pred)
        bb_layout.addStretch()

        # 关闭按钮（右侧）
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
        close_btn.clicked.connect(lambda: self.window().close())  # 关闭父窗口
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
        gradient = QtGui.QRadialGradient(
            rect.center(), max(rect.width(), rect.height()) / 1.2)
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
            p.drawEllipse(QtCore.QPointF(
                star['x'], star['y']), star['size'], star['size'])

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

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
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
            target_pos = screen_center - \
                QtCore.QPoint(self.width() // 2, self.height() //
                              2) - QtCore.QPoint(0, 200)

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
            target_pos = screen_center - \
                QtCore.QPoint(self.width() // 2, self.collapsed_height // 2)

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
