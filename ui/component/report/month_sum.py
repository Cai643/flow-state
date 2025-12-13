import sys
import math
import random
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 导入视觉增强组件
try:
    from ..visual_enhancements.dark_theme_manager import DarkThemeManager
    from ..visual_enhancements.startup_particle_system import StartupParticleSystem
    from ..visual_enhancements.precision_animation_engine import PrecisionAnimationEngine, EasingType
except ImportError:
    # 如果导入失败，创建占位符类
    class DarkThemeManager:
        @staticmethod
        def get_instance():
            return None

    class StartupParticleSystem:
        def __init__(self, parent=None):
            pass

    class PrecisionAnimationEngine:
        def __init__(self, parent=None):
            pass

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

# --- 左栏：竖向时间轴 ---


class TimelineNode(QtWidgets.QWidget):
    clicked = QtCore.Signal(str)  # name

    def __init__(self, date, hours, title, status, is_last=False):
        super().__init__()
        self.date = date
        self.hours = hours
        self.title = title
        self.status = status  # 'completed', 'current', 'locked'
        self.is_last = is_last
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(100)

        # 获取主题管理器
        self.theme_manager = DarkThemeManager.get_instance()

        # 获取动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)

        # 点击粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 闪烁动画 (仅 current) - 使用更平滑的动画
        self.pulse_val = 0.0
        if self.status == 'current':
            self.pulse_animation = AnimatedValue(0.0)
            self.pulse_animation.valueChanged.connect(self._update_pulse_value)
            self._start_pulse_animation()

        # 应用暗色主题
        self._apply_dark_theme()

    def _apply_dark_theme(self):
        """应用暗色主题"""
        if self.theme_manager:
            self.setStyleSheet(f"""
                TimelineNode {{
                    background-color: transparent;
                    border-radius: 8px;
                }}
                TimelineNode:hover {{
                    background-color: rgba(255, 255, 255, 0.05);
                }}
            """)

    def _start_pulse_animation(self):
        """启动脉冲动画"""
        if hasattr(self, 'pulse_animation'):
            # 创建循环脉冲动画
            self.pulse_animation.animate_to(
                1.0, 1000, 0, QtCore.QEasingCurve.InOutSine)

            def reverse_pulse():
                self.pulse_animation.animate_to(
                    0.0, 1000, 0, QtCore.QEasingCurve.InOutSine)
                QtCore.QTimer.singleShot(1000, self._start_pulse_animation)

            QtCore.QTimer.singleShot(1000, reverse_pulse)

    def _update_pulse_value(self, value):
        """更新脉冲值"""
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

        # 获取主题颜色
        if self.theme_manager:
            line_color = self.theme_manager.get_color('border_color')
            accent_color = self.theme_manager.get_color('accent_green')
            text_primary = self.theme_manager.get_color('text_primary')
            text_secondary = self.theme_manager.get_color('text_secondary')
            text_disabled = self.theme_manager.get_color('text_disabled')
        else:
            # 回退颜色
            line_color = QtGui.QColor("#444444")
            accent_color = QtGui.QColor("#00FF88")
            text_primary = QtGui.QColor("#FFFFFF")
            text_secondary = QtGui.QColor("#CCCCCC")
            text_disabled = QtGui.QColor("#666666")

        # 1. 竖线 - 使用发光效果
        if not self.is_last:
            # 主线
            p.setPen(QtGui.QPen(line_color, 3))
            p.drawLine(cx, cy, cx, self.height())

            # 发光效果
            glow_pen = QtGui.QPen(accent_color, 1)
            glow_pen.setStyle(QtCore.Qt.DotLine)
            p.setPen(glow_pen)
            p.drawLine(cx, cy, cx, self.height())

        # 2. 节点圆点 - 增强视觉效果
        radius = 10
        if self.status == 'current':
            # 外层脉冲光环
            pulse_r = radius + 8 * self.pulse_val
            glow_color = QtGui.QColor(accent_color)
            glow_color.setAlpha(int(100 * (1 - self.pulse_val)))

            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(glow_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), pulse_r, pulse_r)

            # 中层光环
            mid_r = radius + 4
            mid_color = QtGui.QColor(accent_color)
            mid_color.setAlpha(150)
            p.setBrush(mid_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), mid_r, mid_r)

            # 核心节点
            p.setBrush(accent_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        elif self.status == 'completed':
            # 完成状态 - 渐变效果
            gradient = QtGui.QRadialGradient(cx, cy, radius)
            gradient.setColorAt(0, accent_color)
            gradient.setColorAt(1, QtGui.QColor(accent_color).darker(150))

            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(gradient)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

            # 外圈发光
            glow_color = QtGui.QColor(accent_color)
            glow_color.setAlpha(80)
            p.setBrush(glow_color)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius + 3, radius + 3)

        else:  # locked
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(text_disabled, 2))
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        # 3. 文字内容 - 使用主题字体和颜色
        text_x = 65

        # 标题 (50h / 100h) - 使用更大更醒目的字体
        if self.status != 'locked':
            p.setPen(accent_color)
        else:
            p.setPen(text_disabled)

        font = QtGui.QFont("Segoe UI", 14, QtGui.QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(text_x, cy + 8, self.hours)

        # 日期 - 右对齐，使用主题颜色
        p.setPen(text_primary)
        font = QtGui.QFont("Segoe UI", 10)
        p.setFont(font)
        fm = QtGui.QFontMetrics(font)
        date_w = fm.horizontalAdvance(self.date)
        p.drawText(self.width() - date_w - 15, cy + 8, self.date)

        # 描述 - 使用次要文字颜色
        p.setPen(text_secondary)
        font = QtGui.QFont("Segoe UI", 11)
        p.setFont(font)
        p.drawText(text_x, cy + 28, self.title)

        # 悬停高亮背景 - 使用主题色彩
        if self.hover_progress.value > 0.01:
            bg_color = QtGui.QColor(accent_color)
            bg_color.setAlpha(int(30 * self.hover_progress.value))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(bg_color)
            p.drawRoundedRect(5, 5, self.width() - 10, 70, 8, 8)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)

    def mousePressEvent(self, event):
        # 触发点击粒子效果
        self._trigger_click_particles()

        # 创建点击动画
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

        # 获取主题管理器
        self.theme_manager = DarkThemeManager.get_instance()

        # 获取动画引擎
        self.animation_engine = PrecisionAnimationEngine(self)

        self.layout = QtWidgets.QVBoxLayout(self)

        # 设置matplotlib暗色主题
        plt.style.use('dark_background')

        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor='none')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.layout.addWidget(self.canvas)

        # 使用更平滑的动画
        self.anim_progress = AnimatedValue(0.0)
        self.anim_progress.valueChanged.connect(self.draw_chart)

        # 粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 数据
        self.weeks = ['W1', 'W2', 'W3', 'W4']
        self.weekly_add = [20, 30, 25, 25]  # 每周新增
        self.cumulative = [20, 50, 75, 100]  # 累计

        # 延迟启动动画，使用更平滑的缓动
        QtCore.QTimer.singleShot(1500, self.start_anim)

    def start_anim(self):
        # 使用更平滑的缓动曲线和更长的动画时间
        self.anim_progress.animate_to(
            1.0, 3000, 0, QtCore.QEasingCurve.OutBack)

        # 动画完成时触发粒子效果
        def on_animation_complete():
            center = QtCore.QPoint(self.width() // 2, self.height() // 2)
            self.particle_system.create_particle_burst(center, 30)
            self.particle_system.show()
            self.particle_system.trigger_startup_effect(center)

        QtCore.QTimer.singleShot(3000, on_animation_complete)

    def draw_chart(self, progress):
        self.figure.clear()

        # 获取主题颜色
        if self.theme_manager:
            accent_green = self.theme_manager.COLORS['accent_green']
            accent_blue = self.theme_manager.COLORS['accent_blue']
            text_primary = self.theme_manager.COLORS['text_primary']
            text_secondary = self.theme_manager.COLORS['text_secondary']
            border_color = self.theme_manager.COLORS['border_color']
        else:
            accent_green = '#00FF88'
            accent_blue = '#4ECDC4'
            text_primary = '#FFFFFF'
            text_secondary = '#CCCCCC'
            border_color = '#4a4a4a'

        # 双Y轴
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()

        ax1.set_facecolor('none')
        ax2.set_facecolor('none')

        # 设置样式 - 使用主题颜色
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['bottom'].set_color(border_color)
        ax1.spines['left'].set_color(border_color)
        ax1.tick_params(axis='x', colors=text_primary, labelsize=10)
        ax1.tick_params(axis='y', colors=accent_blue, labelsize=10)

        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_color(border_color)
        ax2.tick_params(axis='y', colors=accent_green, labelsize=10)

        x = np.arange(len(self.weeks))

        # 1. 柱状图 (每周新增) - 使用主题绿色，增加渐变效果
        bar_heights = [h * progress for h in self.weekly_add]
        bars = ax2.bar(x, bar_heights, color=accent_green,
                       alpha=0.7, width=0.5, label='每周新增',
                       edgecolor=accent_green, linewidth=2)

        # 为柱状图添加发光效果
        for bar in bars:
            bar.set_glow_effect = True

        ax2.set_ylim(0, 40)

        # 2. 折线图 (累计) - 使用主题蓝色，增强视觉效果
        num_points = len(self.weeks)
        current_idx = progress * (num_points - 1)
        idx_int = int(current_idx)
        idx_frac = current_idx - idx_int

        if progress > 0:
            xs = x[:idx_int+1]
            ys = self.cumulative[:idx_int+1]

            # 插值最后一个点
            if idx_int < num_points - 1:
                next_x = x[idx_int+1]
                next_y = self.cumulative[idx_int+1]
                curr_x = x[idx_int]
                curr_y = self.cumulative[idx_int]

                interp_x = curr_x + (next_x - curr_x) * idx_frac
                interp_y = curr_y + (next_y - curr_y) * idx_frac

                xs = np.append(xs, interp_x)
                ys = np.append(ys, interp_y)

            # 主线条 - 更粗更亮
            ax1.plot(xs, ys, color=accent_blue, linewidth=4,
                     marker='o', markersize=8, markerfacecolor=accent_blue,
                     markeredgecolor='white', markeredgewidth=2,
                     label='累计时长', alpha=0.9)

            # 区域填充 - 渐变效果
            ax1.fill_between(xs, 0, ys, color=accent_blue, alpha=0.2)

            # 添加数据点标签
            for i, (xi, yi) in enumerate(zip(xs, ys)):
                if i < len(self.cumulative):
                    ax1.annotate(f'{int(self.cumulative[i])}h',
                                 (xi, yi), textcoords="offset points",
                                 xytext=(0, 10), ha='center',
                                 color=text_primary, fontsize=9, fontweight='bold')

        ax1.set_ylim(0, 150)
        ax1.set_xticks(x)
        ax1.set_xticklabels(self.weeks, color=text_primary,
                            fontsize=11, fontweight='bold')

        # 添加网格线
        ax1.grid(True, alpha=0.3, color=border_color, linestyle='--')

        # 设置标签
        ax1.set_ylabel('累计时长 (小时)', color=accent_blue,
                       fontsize=12, fontweight='bold')
        ax2.set_ylabel('每周新增 (小时)', color=accent_green,
                       fontsize=12, fontweight='bold')

        self.canvas.draw()

# --- 右栏：下月计划 ---


class CheckBoxItem(QtWidgets.QWidget):
    def __init__(self, text, checked=False):
        super().__init__()

        # 获取主题管理器
        self.theme_manager = DarkThemeManager.get_instance()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setChecked(checked)

        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            border_color = self.theme_manager.COLORS['border_color']
            bg_color = self.theme_manager.COLORS['background_secondary']
            self.checkbox.setStyleSheet(f"""
                QCheckBox::indicator {{ 
                    width: 20px; 
                    height: 20px; 
                    border: 2px solid {border_color}; 
                    border-radius: 4px;
                    background-color: {bg_color};
                }}
                QCheckBox::indicator:checked {{ 
                    background-color: {accent_color}; 
                    border-color: {accent_color};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {accent_color};
                }}
            """)
        else:
            self.checkbox.setStyleSheet("""
                QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #4a4a4a; border-radius: 4px; }
                QCheckBox::indicator:checked { background-color: #00FF88; border-color: #00FF88; }
            """)

        label = QtWidgets.QLabel(text)
        if self.theme_manager:
            text_primary = self.theme_manager.COLORS['text_primary']
            label.setStyleSheet(f"""
                QLabel {{
                    color: {text_primary};
                    font-size: 14px;
                    font-family: 'Segoe UI', sans-serif;
                }}
            """)
        else:
            label.setStyleSheet("color: #FFFFFF; font-size: 14px;")

        layout.addWidget(self.checkbox)
        layout.addWidget(label)
        layout.addStretch()


class NextMonthPlan(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # 获取主题管理器
        self.theme_manager = DarkThemeManager.get_instance()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # 标题 - 使用主题颜色
        title = QtWidgets.QLabel("🎯 下月挑战计划")
        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            title.setStyleSheet(f"""
                QLabel {{
                    color: {accent_color};
                    font-size: 18px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                    margin-bottom: 10px;
                }}
            """)
        else:
            title.setStyleSheet(
                "color: #00FF88; font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)

        # 目标进度
        target_box = QtWidgets.QWidget()
        tb_layout = QtWidgets.QVBoxLayout(target_box)
        tb_layout.setContentsMargins(0, 10, 0, 10)

        lbl_target = QtWidgets.QLabel("目标：突破 150 小时")
        if self.theme_manager:
            text_primary = self.theme_manager.COLORS['text_primary']
            lbl_target.setStyleSheet(f"""
                QLabel {{
                    color: {text_primary};
                    font-size: 16px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                }}
            """)
        else:
            lbl_target.setStyleSheet(
                "color: #FFFFFF; font-size: 16px; font-weight: bold;")

        # 进度条 - 使用QProgressBar并应用主题样式
        progress_bar = QtWidgets.QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(150)
        progress_bar.setValue(100)
        progress_bar.setFixedHeight(12)

        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            bg_color = self.theme_manager.COLORS['background_secondary']
            progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {bg_color};
                    border: 1px solid {self.theme_manager.COLORS['border_color']};
                    border-radius: 6px;
                    text-align: center;
                    color: {self.theme_manager.COLORS['text_primary']};
                    font-weight: bold;
                    font-size: 10px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {accent_color}, 
                        stop:1 {self.theme_manager.COLORS['accent_green_light']});
                    border-radius: 5px;
                }}
            """)
        else:
            progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #444444;
                    border-radius: 6px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #00FF88;
                    border-radius: 5px;
                }
            """)

        lbl_curr = QtWidgets.QLabel("当前进度: 100h / 150h (66.7%)")
        if self.theme_manager:
            text_secondary = self.theme_manager.COLORS['text_secondary']
            lbl_curr.setStyleSheet(f"""
                QLabel {{
                    color: {text_secondary};
                    font-size: 12px;
                    font-family: 'Segoe UI', sans-serif;
                }}
            """)
        else:
            lbl_curr.setStyleSheet("color: #CCCCCC; font-size: 12px;")

        tb_layout.addWidget(lbl_target)
        tb_layout.addWidget(progress_bar)
        tb_layout.addWidget(lbl_curr)

        self.layout.addWidget(target_box)

        # 建议策略
        lbl_adv = QtWidgets.QLabel("💡 建议策略:")
        if self.theme_manager:
            text_secondary = self.theme_manager.COLORS['text_secondary']
            lbl_adv.setStyleSheet(f"""
                QLabel {{
                    color: {text_secondary};
                    font-size: 15px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                    margin-top: 15px;
                    margin-bottom: 10px;
                }}
            """)
        else:
            lbl_adv.setStyleSheet(
                "color: #CCCCCC; font-size: 15px; font-weight: bold; margin-top: 15px;")
        self.layout.addWidget(lbl_adv)

        self.layout.addWidget(CheckBoxItem("保持上午9-11点黄金时段", True))
        self.layout.addWidget(CheckBoxItem("减少下午3点后低效任务", True))
        self.layout.addWidget(CheckBoxItem("周末适当放松 (不设目标)", False))

        self.layout.addStretch()

        # 按钮 - 使用主题样式
        btn = QtWidgets.QPushButton("🚀 生成我的月计划")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFixedHeight(45)

        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            bg_color = self.theme_manager.COLORS['background_card']
            text_primary = self.theme_manager.COLORS['text_primary']
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 255, 136, 0.2), 
                        stop:1 rgba(0, 255, 136, 0.1));
                    color: {accent_color};
                    border: 2px solid {accent_color};
                    border-radius: 10px;
                    padding: 12px;
                    font-weight: bold;
                    font-size: 14px;
                    font-family: 'Segoe UI', sans-serif;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {accent_color}, 
                        stop:1 rgba(0, 255, 136, 0.8));
                    color: {self.theme_manager.COLORS['background_primary']};
                    border-color: {accent_color};
                }}
                QPushButton:pressed {{
                    background-color: {self.theme_manager.COLORS['accent_green_dark']};
                    color: {text_primary};
                }}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 255, 136, 0.2);
                    color: #00FF88;
                    border: 2px solid #00FF88;
                    border-radius: 10px;
                    padding: 12px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #00FF88;
                    color: #1a1a1a;
                }
            """)

        btn.clicked.connect(self.generate_plan)
        self.layout.addWidget(btn)

    def generate_plan(self):
        QtWidgets.QMessageBox.information(
            self, "计划生成", "已根据您的策略生成下月日历！\n高效时段已自动标记。")

# --- 主界面 ---


class MilestoneReport(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.resize(1000, 700)
        self.drag_start_pos = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)

        # 获取主题管理器和动画引擎
        self.theme_manager = DarkThemeManager.get_instance()
        self.animation_engine = PrecisionAnimationEngine(self)

        # 创建启动粒子效果系统
        self.particle_system = StartupParticleSystem(self)
        self.particle_system.hide()

        # 应用暗色主题背景
        self.setAutoFillBackground(True)
        if self.theme_manager:
            bg_color = self.theme_manager.get_color('background_primary')
            self.setStyleSheet(f"""
                MilestoneReport {{
                    background-color: {self.theme_manager.COLORS['background_primary']};
                    border-radius: 15px;
                }}
            """)
        else:
            p = self.palette()
            p.setColor(self.backgroundRole(), QtGui.QColor("#1a1a1a"))
            self.setPalette(p)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # 顶部标题 - 使用主题颜色和更好的字体
        title_lbl = QtWidgets.QLabel("🎉 恭喜！本月专注突破 100 小时！")
        title_lbl.setAlignment(QtCore.Qt.AlignCenter)

        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            title_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {accent_color};
                    font-size: 28px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                    margin-bottom: 25px;
                    padding: 15px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 255, 136, 0.1), 
                        stop:0.5 rgba(0, 255, 136, 0.05),
                        stop:1 rgba(0, 255, 136, 0.1));
                    border-radius: 12px;
                }}
            """)
        else:
            title_lbl.setStyleSheet(
                "color: #00FF88; font-size: 28px; font-weight: bold; margin-bottom: 25px;")

        main_layout.addWidget(title_lbl)

        # 触发启动粒子效果
        QtCore.QTimer.singleShot(500, self._trigger_startup_particles)

        # 中间三栏内容
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(30)

        # 左栏：时间轴 - 使用主题样式
        left_box = QtWidgets.QGroupBox("📈 成长足迹")
        self._apply_groupbox_style(left_box)
        lb_layout = QtWidgets.QVBoxLayout(left_box)
        lb_layout.addWidget(TimelinePanel())
        content_layout.addWidget(left_box, 1)

        # 中栏：曲线图 - 使用主题样式
        mid_box = QtWidgets.QGroupBox("📊 成长曲线")
        self._apply_groupbox_style(mid_box)
        mb_layout = QtWidgets.QVBoxLayout(mid_box)
        mb_layout.addWidget(GrowthChart())
        content_layout.addWidget(mid_box, 2)  # 占宽一点

        # 右栏：计划 - 使用主题样式
        right_box = QtWidgets.QGroupBox("🎯 下月规划")
        self._apply_groupbox_style(right_box)
        rb_layout = QtWidgets.QVBoxLayout(right_box)
        rb_layout.addWidget(NextMonthPlan())
        content_layout.addWidget(right_box, 1)

        main_layout.addLayout(content_layout)

        # 底部预测条 (简化版)
        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setFixedHeight(40)
        bb_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(0, 0, 0, 0)

        lbl_pred = QtWidgets.QLabel("🚀 预测：按此趋势，下月有望达到 135 小时！")
        if self.theme_manager:
            accent_blue = self.theme_manager.COLORS['accent_blue']
            lbl_pred.setStyleSheet(f"""
                QLabel {{
                    color: {accent_blue};
                    font-size: 16px;
                    font-weight: bold;
                    font-family: 'Segoe UI', sans-serif;
                    padding: 8px 15px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(78, 205, 196, 0.1), 
                        stop:1 rgba(78, 205, 196, 0.05));
                    border-radius: 8px;
                }}
            """)
        else:
            lbl_pred.setStyleSheet(
                "color: #4ECDC4; font-size: 16px; font-weight: bold;")
        bb_layout.addWidget(lbl_pred)
        bb_layout.addStretch()

        # 关闭按钮 - 使用主题样式
        close_btn = QtWidgets.QPushButton("✕ 关闭")
        close_btn.setFixedSize(100, 35)
        if self.theme_manager:
            self.theme_manager.apply_theme_to_widget(close_btn)
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme_manager.COLORS['background_card']};
                    color: {self.theme_manager.COLORS['text_primary']};
                    border: 2px solid {self.theme_manager.COLORS['border_color']};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme_manager.COLORS['accent_green']};
                    color: {self.theme_manager.COLORS['background_primary']};
                    border-color: {self.theme_manager.COLORS['accent_green']};
                }}
                QPushButton:pressed {{
                    background-color: {self.theme_manager.COLORS['accent_green_dark']};
                }}
            """)
        else:
            close_btn.setStyleSheet(
                "background-color: #3a3a3a; color: white; border-radius: 8px; font-weight: bold;")

        close_btn.clicked.connect(self.close)
        bb_layout.addWidget(close_btn)

        main_layout.addWidget(bottom_bar)

    def _apply_groupbox_style(self, groupbox):
        """应用GroupBox的主题样式"""
        if self.theme_manager:
            accent_color = self.theme_manager.COLORS['accent_green']
            bg_color = self.theme_manager.COLORS['background_card']
            border_color = self.theme_manager.COLORS['border_color']
            text_primary = self.theme_manager.COLORS['text_primary']

            groupbox.setStyleSheet(f"""
                QGroupBox {{
                    color: {text_primary};
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 15px;
                    margin-top: 15px;
                    font-weight: bold;
                    font-size: 14px;
                    padding-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 15px;
                    padding: 0 8px 0 8px;
                    color: {accent_color};
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
        else:
            groupbox.setStyleSheet(
                "QGroupBox { color: #FFFFFF; border: 2px solid #4a4a4a; border-radius: 15px; margin-top: 15px; } QGroupBox::title { subcontrol-origin: margin; left: 15px; color: #00FF88; }")

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
        # 创建入场动画
        if hasattr(self, 'animation_engine'):
            entrance_anim = self.animation_engine.create_combined_entrance_animation(
                self, 800)
            if entrance_anim:
                entrance_anim.start()

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
