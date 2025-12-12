import sys
import math
import random
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

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
    clicked = QtCore.Signal(str) # name

    def __init__(self, date, hours, title, status, is_last=False):
        super().__init__()
        self.date = date
        self.hours = hours
        self.title = title
        self.status = status # 'completed', 'current', 'locked'
        self.is_last = is_last
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(100)
        
        self.hover_progress = AnimatedValue(0.0)
        self.hover_progress.valueChanged.connect(self.update)
        
        # 闪烁动画 (仅 current)
        self.pulse_val = 0.0
        if self.status == 'current':
            self.pulse_timer = QtCore.QTimer(self)
            self.pulse_timer.timeout.connect(self.update_pulse)
            self.pulse_timer.start(50)
            self.pulse_dir = 1

    def update_pulse(self):
        self.pulse_val += 0.05 * self.pulse_dir
        if self.pulse_val >= 1.0:
            self.pulse_val = 1.0
            self.pulse_dir = -1
        elif self.pulse_val <= 0.0:
            self.pulse_val = 0.0
            self.pulse_dir = 1
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        cx = 30
        cy = 20
        
        # 1. 竖线
        if not self.is_last:
            p.setPen(QtGui.QPen(QtGui.QColor("#444444"), 2))
            p.drawLine(cx, cy, cx, self.height())
            
        # 2. 节点圆点
        radius = 8
        if self.status == 'current':
            # 闪烁光环
            pulse_r = radius + 6 * self.pulse_val
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(241, 196, 15, 100)) # 半透明金
            p.drawEllipse(QtCore.QPointF(cx, cy), pulse_r, pulse_r)
            
            p.setBrush(QtGui.QColor("#F1C40F"))
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        elif self.status == 'completed':
            p.setBrush(QtGui.QColor("#F1C40F"))
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
        else: # locked
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor("#95A5A6"), 2))
            p.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)
            
        # 3. 文字内容
        text_x = 60
        
        # 标题 (50h / 100h)
        p.setPen(QtGui.QColor("#F1C40F") if self.status != 'locked' else QtGui.QColor("#95A5A6"))
        font = QtGui.QFont("Microsoft YaHei", 12, QtGui.QFont.Bold)
        p.setFont(font)
        p.drawText(text_x, cy + 5, self.hours)
        
        # 日期
        p.setPen(QtGui.QColor("#DDDDDD"))
        font.setPixelSize(10)
        font.setBold(False)
        p.setFont(font)
        fm = QtGui.QFontMetrics(font)
        date_w = fm.horizontalAdvance(self.date)
        p.drawText(self.width() - date_w - 10, cy + 5, self.date)
        
        # 描述
        p.setPen(QtGui.QColor("#AAAAAA"))
        font.setPixelSize(11)
        p.setFont(font)
        p.drawText(text_x, cy + 25, self.title)
        
        # 悬停高亮背景
        if self.hover_progress.value > 0.01:
            bg_color = QtGui.QColor(255, 255, 255, int(20 * self.hover_progress.value))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(bg_color)
            p.drawRoundedRect(0, 0, self.width(), 60, 5, 5)

    def enterEvent(self, event):
        self.hover_progress.animate_to(1.0, 200)

    def leaveEvent(self, event):
        self.hover_progress.animate_to(0.0, 200)
        
    def mousePressEvent(self, event):
        if self.status == 'completed':
            QtWidgets.QMessageBox.information(self, "里程碑回顾", f"查看 {self.hours} 达成时的详细周报...")
        elif self.status == 'locked':
             QtWidgets.QMessageBox.information(self, "目标设定", f"设定下个月目标为 {self.hours}？")

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
        self.layout = QtWidgets.QVBoxLayout(self)
        self.figure = Figure(figsize=(5, 4), dpi=100, facecolor='none')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.layout.addWidget(self.canvas)
        
        self.anim_progress = AnimatedValue(0.0)
        self.anim_progress.valueChanged.connect(self.draw_chart)
        
        # 数据
        self.weeks = ['W1', 'W2', 'W3', 'W4']
        self.weekly_add = [20, 30, 25, 25] # 每周新增
        self.cumulative = [20, 50, 75, 100] # 累计
        
        QtCore.QTimer.singleShot(1000, self.start_anim)

    def start_anim(self):
        self.anim_progress.animate_to(1.0, 2000, 0, QtCore.QEasingCurve.OutCubic)

    def draw_chart(self, progress):
        self.figure.clear()
        
        # 双Y轴
        ax1 = self.figure.add_subplot(111)
        ax2 = ax1.twinx()
        
        ax1.set_facecolor('none')
        ax2.set_facecolor('none')
        
        # 设置样式
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['bottom'].set_color('#666666')
        ax1.spines['left'].set_color('#666666')
        ax1.tick_params(axis='x', colors='#DDDDDD')
        ax1.tick_params(axis='y', colors='#3498db') # 累计轴颜色
        
        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_color('#666666')
        ax2.tick_params(axis='y', colors='#2ecc71') # 新增轴颜色
        
        x = np.arange(len(self.weeks))
        
        # 1. 柱状图 (每周新增) - 绿色
        # 动画：从下往上长
        bar_heights = [h * progress for h in self.weekly_add]
        ax2.bar(x, bar_heights, color='#2ecc71', alpha=0.3, width=0.4, label='每周新增')
        ax2.set_ylim(0, 40)
        
        # 2. 折线图 (累计) - 蓝色
        # 动画：从左往右画
        # 计算当前显示多少个点
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
                
            ax1.plot(xs, ys, color='#3498db', linewidth=2, marker='o', label='累计时长')
            # 区域填充
            ax1.fill_between(xs, 0, ys, color='#3498db', alpha=0.1)
            
        ax1.set_ylim(0, 150)
        ax1.set_xticks(x)
        ax1.set_xticklabels(self.weeks)
        
        self.canvas.draw()

# --- 右栏：下月计划 ---
class CheckBoxItem(QtWidgets.QWidget):
    def __init__(self, text, checked=False):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        self.checkbox = QtWidgets.QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #888; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #F1C40F; border-color: #F1C40F; }
        """)
        
        label = QtWidgets.QLabel(text)
        label.setStyleSheet("color: #DDDDDD; font-size: 13px;")
        
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
        title.setStyleSheet("color: #F1C40F; font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title)
        
        # 目标进度
        target_box = QtWidgets.QWidget()
        tb_layout = QtWidgets.QVBoxLayout(target_box)
        tb_layout.setContentsMargins(0, 10, 0, 10)
        
        lbl_target = QtWidgets.QLabel("目标：突破 150 小时")
        lbl_target.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        
        # 进度条
        progress_bg = QtWidgets.QFrame()
        progress_bg.setFixedHeight(8)
        progress_bg.setStyleSheet("background-color: #444444; border-radius: 4px;")
        
        progress_fill = QtWidgets.QFrame(progress_bg)
        progress_fill.setGeometry(0, 0, int(progress_bg.width() * 0.66), 8) # 100/150 approx
        progress_fill.setStyleSheet("background-color: #F1C40F; border-radius: 4px;")
        
        # 这里由于是在初始化时，geometry可能还未确定，实际应用中建议用 paintEvent 绘制或 Layout
        # 简化处理：显示文字
        lbl_curr = QtWidgets.QLabel("当前进度: 100h / 150h")
        lbl_curr.setStyleSheet("color: #888888; font-size: 12px;")
        
        tb_layout.addWidget(lbl_target)
        tb_layout.addWidget(progress_bg) # 占位
        tb_layout.addWidget(lbl_curr)
        
        self.layout.addWidget(target_box)
        
        # 建议策略
        lbl_adv = QtWidgets.QLabel("建议策略:")
        lbl_adv.setStyleSheet("color: #AAAAAA; font-size: 13px; margin-top: 10px;")
        self.layout.addWidget(lbl_adv)
        
        self.layout.addWidget(CheckBoxItem("保持上午9-11点黄金时段", True))
        self.layout.addWidget(CheckBoxItem("减少下午3点后低效任务", True))
        self.layout.addWidget(CheckBoxItem("周末适当放松 (不设目标)", False))
        
        self.layout.addStretch()
        
        # 按钮
        btn = QtWidgets.QPushButton("生成我的月计划")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(241, 196, 15, 0.2);
                color: #F1C40F;
                border: 1px solid #F1C40F;
                border-radius: 5px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(241, 196, 15, 0.4);
            }
        """)
        btn.clicked.connect(self.generate_plan)
        self.layout.addWidget(btn)
        
    def generate_plan(self):
        QtWidgets.QMessageBox.information(self, "计划生成", "已根据您的策略生成下月日历！\n高效时段已自动标记。")

# --- 主界面 ---
class MilestoneReport(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.resize(1000, 700)
        self.drag_start_pos = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        
        # 背景
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QtGui.QColor("#111111"))
        self.setPalette(p)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        
        # 顶部标题
        title_lbl = QtWidgets.QLabel("🎉 恭喜！本月专注突破 100 小时！")
        title_lbl.setAlignment(QtCore.Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #F1C40F; font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        main_layout.addWidget(title_lbl)
        
        # 中间三栏内容
        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(30)
        
        # 左栏：时间轴
        left_box = QtWidgets.QGroupBox("成长足迹")
        left_box.setStyleSheet("QGroupBox { color: #888888; border: 1px solid #333; border-radius: 10px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        lb_layout = QtWidgets.QVBoxLayout(left_box)
        lb_layout.addWidget(TimelinePanel())
        content_layout.addWidget(left_box, 1)
        
        # 中栏：曲线图
        mid_box = QtWidgets.QGroupBox("成长曲线")
        mid_box.setStyleSheet("QGroupBox { color: #888888; border: 1px solid #333; border-radius: 10px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        mb_layout = QtWidgets.QVBoxLayout(mid_box)
        mb_layout.addWidget(GrowthChart())
        content_layout.addWidget(mid_box, 2) # 占宽一点
        
        # 右栏：计划
        right_box = QtWidgets.QGroupBox("下月规划")
        right_box.setStyleSheet("QGroupBox { color: #888888; border: 1px solid #333; border-radius: 10px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
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
        lbl_pred.setStyleSheet("color: #3498db; font-size: 14px; font-weight: bold;")
        bb_layout.addWidget(lbl_pred)
        bb_layout.addStretch()
        
        # 关闭按钮
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.setFixedSize(80, 30)
        close_btn.setStyleSheet("background-color: #333; color: white; border-radius: 5px;")
        close_btn.clicked.connect(self.close)
        bb_layout.addWidget(close_btn)
        
        main_layout.addWidget(bottom_bar)

    def mousePressEvent(self, event):
        # 允许拖动
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_start_pos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_start_pos is not None and event.button() == QtCore.Qt.LeftButton:
            drag_distance = (event.globalPos() - self.drag_start_pos).manhattanLength()
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
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        
    window = MilestoneReport()
    window.show()
    
    if not QtWidgets.QApplication.instance():
        sys.exit(app.exec())
    else:
        app.exec()

if __name__ == "__main__":
    show_milestone_report()
