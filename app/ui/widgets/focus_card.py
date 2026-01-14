try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal

import os
import sys

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 导入统一主题
try:
    from app.ui.widgets.report.theme import theme as MorandiTheme
except ImportError:
    try:
        from app.ui.widgets.report.theme import theme as MorandiTheme
    except ImportError:
        # Fallback if relative import fails
        from app.ui.widgets.report.theme import theme as MorandiTheme

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class FocusStatusCard(QtWidgets.QWidget):
    """
    专注状态卡片
    展示核心状态和摘要
    """
    enter_deep_mode_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)

        self.hovering = False
        
        # 拉回注意力次数（从娱乐 -> 工作 的切换次数）
        self.pull_back_count = 0
        self.last_status = None

        # 构建 UI
        self._build_ui()

        # 呼吸动画定时器（极轻微透明度变化）
        self.breath_value = 0.0
        self.breath_direction = 1
        self.breath_timer = QtCore.QTimer(self)
        self.breath_timer.setInterval(120)
        self.breath_timer.timeout.connect(self._update_breath)
        self.breath_timer.start()

        self._apply_style()

    def sizeHint(self):
        # 基础高度 (标题30 + 状态30 + 摘要30 + 间距 + 边距)
        return QtCore.QSize(250, 150)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.item_style = """
            QLabel {
                background-color: #FEFAE0;
                border-radius: 12px;
                padding: 4px 12px;
                color: #5D4037;
            }
        """

        # 核心状态
        self.title_label = QtWidgets.QLabel("🎯 今日专注  0.0h / 8h")
        title_font = QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.DemiBold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(self.item_style)
        self.title_label.setFixedHeight(30)

        self.status_label = QtWidgets.QLabel("⚡ 专注中  已连续0分钟")
        self.status_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet(self.item_style)
        self.status_label.setFixedHeight(30)

        self.summary_label = QtWidgets.QLabel("💪 拉回注意力 0次  ↑效率+0%")
        self.summary_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.summary_label.setStyleSheet(self.item_style)
        self.summary_label.setFixedHeight(30)

        layout.addWidget(self.title_label)
        layout.addSpacing(2)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)

    def enterEvent(self, event):
        self.hovering = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovering = False
        self._apply_style()
        super().leaveEvent(event)

    def _apply_style(self):
        # --- 样式参数调节区 ---
        # 清新森林主题基色: #66BB6A (Green)

        # 背景与边框完全不透明
        bg_color = QtGui.QColor("#7FA10F")
        bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 255)"
        border_color = QtGui.QColor("#7FA10F")
        border_rgba = f"rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 255)"

        text_color = "#5D4037"
        
        # 悬停时稍微变亮或加深边框
        if self.hovering:
             border_color = border_color.lighter(110)
             border_rgba = f"rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 255)"

        style = """
            QWidget {
                background-color: %s;
                border-radius: 16px;
                border: 1px solid %s;
                color: %s;
            }
        """
        self.setStyleSheet(style % (bg_rgba, border_rgba, text_color))

    def _update_breath(self):
        # 0.95 -> 1.0 的轻微呼吸效果
        step = 0.02
        self.breath_value += step * self.breath_direction
        if self.breath_value > 1.0:
            self.breath_value = 1.0
            self.breath_direction = -1
        elif self.breath_value < 0.0:
            self.breath_value = 0.0
            self.breath_direction = 1
        # self._apply_style() # 减少频繁调用以优化性能，或者仅在需要时更新

    # 对外数据更新接口：联动监控结果
    def update_from_result(self, result: dict):
        # status = "working" # 这里的 status 应该从 result 中获取
        # 暂时保留原有模拟逻辑，实际应解析 result
        
        display_focus_hours = 4.5
        target_hours = 8.0
        
        self.title_label.setText(
            f"🎯 今日专注  {display_focus_hours:.1f}h / {target_hours:.0f}h")

        display_minutes = 25
        efficiency_gain = 30
        display_pull_back_count = 10

        self.status_label.setText(f"⚡ 专注中  已连续{display_minutes}分钟")

        self.summary_label.setText(
            f"💪 拉回注意力 {display_pull_back_count}次  ↑效率+{efficiency_gain}%"
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    # 创建黑色背景窗口，模拟屏幕环境
    bg_window = QtWidgets.QWidget()
    bg_window.setStyleSheet("background-color: #1a1a1a;")
    bg_window.resize(400, 300)

    # 将卡片放在背景窗口中
    card = FocusStatusCard(bg_window)
    card.move(50, 50)

    # 模拟一些数据更新
    def mock_update():
        import random
        status = random.choice(
            ["working", "working", "working", "entertainment", "idle"])
        duration = random.randint(0, 3600*4)
        card.update_from_result({"status": status, "duration": duration})

    timer = QtCore.QTimer()
    timer.timeout.connect(mock_update)
    timer.start(3000)

    bg_window.show()

    sys.exit(app.exec())
