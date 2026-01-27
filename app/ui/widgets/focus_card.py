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

    修改：保留统计，更改为专注/充能模式转换
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

        # 模式切换 Switch 按钮容器
        mode_container = QtWidgets.QWidget()
        mode_layout = QtWidgets.QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)
        
        # 专注模式按钮
        self.focus_btn = QtWidgets.QPushButton("💪 专注模式")
        self.focus_btn.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.focus_btn.setCheckable(True)
        self.focus_btn.setChecked(True)
        self.focus_btn.setFixedHeight(30)
        self.focus_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.focus_btn.clicked.connect(self._on_focus_mode_clicked)
        
        # 充电模式按钮
        self.recharge_btn = QtWidgets.QPushButton("🔋 充电模式")
        self.recharge_btn.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.recharge_btn.setCheckable(True)
        self.recharge_btn.setChecked(False)
        self.recharge_btn.setFixedHeight(30)
        self.recharge_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.recharge_btn.clicked.connect(self._on_recharge_mode_clicked)
        
        mode_layout.addWidget(self.focus_btn, 1)
        mode_layout.addWidget(self.recharge_btn, 1)
        mode_container.setFixedHeight(30)
        
        # 当前模式 (用于跟踪状态)
        self.current_mode = "focus"
        self._update_mode_buttons_style()

        layout.addWidget(self.title_label)
        layout.addSpacing(2)
        layout.addWidget(self.status_label)
        layout.addWidget(mode_container)

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

    def _update_mode_buttons_style(self):
        """更新模式按钮的样式"""
        if self.current_mode == "focus":
            # 专注模式：深绿底白字
            self.focus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            # 充电模式：浅绿底黑字
            self.recharge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEFAE0;
                    color: #5D4037;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #FFFEF5;
                }
            """)
        else:
            # 专注模式：浅绿底黑字
            self.focus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FEFAE0;
                    color: #5D4037;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #FFFEF5;
                }
            """)
            # 充电模式：深绿底白字
            self.recharge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)

    def _on_focus_mode_clicked(self):
        """处理专注模式按钮点击"""
        if self.current_mode != "focus":
            self.current_mode = "focus"
            self._update_mode_buttons_style()
            # 更新全局模式
            from app.data.services.history_service import ActivityHistoryManager
            ActivityHistoryManager.set_current_mode("focus")

    def _on_recharge_mode_clicked(self):
        """处理充电模式按钮点击"""
        if self.current_mode != "recharge":
            self.current_mode = "recharge"
            self._update_mode_buttons_style()
            # 更新全局模式
            from app.data.services.history_service import ActivityHistoryManager
            ActivityHistoryManager.set_current_mode("recharge")

    # 对外数据更新接口：联动监控结果
    def update_from_result(self, result: dict):
        # 1. 解析实时监控数据
        current_status = result.get("status", "focus")
        current_duration = result.get("duration", 0) # 秒
        
        # 2. 查询今日累计数据 (调用 StatsDAO)
        try:
            # 修正导入：StatsDAO 位于 app.data.dao.activity_dao
            from app.data.dao.activity_dao import StatsDAO
            from datetime import date
            
            # 调试：打印一下，看看是否真的查到了数据
            # print(f"FocusCard: Querying StatsDAO for {date.today()}...")
            
            summary = StatsDAO.get_daily_summary(date.today())
            total_focus_sec = 0
            if summary:
                # 兼容可能的字典键名差异 (focus_time vs total_focus_time)
                # 检查 activity_dao.py 实际返回的键名
                f_time = summary.get('total_focus_time') or summary.get('focus_time') or 0
                w_time = summary.get('total_work_time') or summary.get('work_time') or 0
                
                total_focus_sec = f_time + w_time
                # print(f"FocusCard: DB Stats -> Focus: {f_time}, Work: {w_time}, Total: {total_focus_sec}")
            
            # 加上当前这一段还没入库的时长 (如果当前状态也是工作/专注)
            if current_status in ['work', 'focus']:
                total_focus_sec += current_duration
                
            display_focus_hours = total_focus_sec / 3600.0
            
        except ImportError:
            # 如果是在独立测试运行，可能无法导入
            # print("FocusCard: ImportError - app.data.dao.activity_dao")
            display_focus_hours = 0.0
        except Exception as e:
            print(f"Stats error: {e}")
            display_focus_hours = 0.0

        # 3. 计算“拉回注意力”次数 (从娱乐 -> 工作/专注 的切换)
        # 修改：充电模式下不计算拉回注意力次数
        if self.last_status is not None and self.current_mode != "recharge":
            # 只有当上一次是娱乐，且这一次变成了工作或专注，才算一次“拉回”
            if self.last_status == 'entertainment' and current_status in ['work', 'focus']:
                self.pull_back_count += 1
        
        self.last_status = current_status

        target_hours = 8.0
        self.title_label.setText(
            f"🎯 今日专注  {display_focus_hours:.1f}h / {target_hours:.0f}h")

        # 修改：使用当前状态的持续时间，而不是总的 current_duration
        # 这里的 result['current_window_duration'] 可能不存在，我们需要检查 thread.py 传递了什么
        # 之前我们在 thread.py 中添加了 current_window_duration 字段
        
        # 实际上，current_duration 已经是总持续时间了 (time.time() - status_start_time)
        # 所以直接用 current_duration 显示 "已连续XX分钟" 是对的
        display_minutes = int(current_duration / 60)
        
        # efficiency_gain = 30 # 暂时保留模拟值，后续可改为基于算法计算
        
        # 简单算法：每拉回一次，效率提升 5%，上限 50%
        efficiency_gain = min(self.pull_back_count * 5, 50)
        
        display_pull_back_count = self.pull_back_count

        if self.current_mode == "recharge":
            self.status_label.setText(f"🔋 充电中  已连续{display_minutes}分钟")
        else:
            self.status_label.setText(f"⚡ 专注中  已连续{display_minutes}分钟")


class TimerDialog(QtWidgets.QDialog):
    """
    轻量级番茄钟计时器悬浮窗
    """
    end_session_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.setFixedSize(200, 80)
        
        self._build_ui()
        self._dragging = False
        self._drag_start_pos = QtCore.QPoint()

    def _build_ui(self):
        # 背景容器
        self.container = QtWidgets.QWidget(self)
        self.container.setGeometry(0, 0, 200, 80)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #FF7043;
                border-radius: 15px;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # 倒计时显示
        self.time_label = QtWidgets.QLabel("25:00")
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            color: #D84315;
            font-size: 28px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.time_label)
        
        # 目标提示 (可选，鼠标悬停显示或一直显示小字)
        self.goal_label = QtWidgets.QLabel("专注中...")
        self.goal_label.setAlignment(QtCore.Qt.AlignCenter)
        self.goal_label.setStyleSheet("""
            color: #FF7043;
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.goal_label)

    def start_session(self, goal_text, total_seconds):
        self.goal_label.setText(goal_text)
        self.update_display(total_seconds)

    def update_display(self, remaining_seconds):
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & QtCore.Qt.LeftButton):
            self.move(event.globalPos() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def mouseDoubleClickEvent(self, event):
        # 双击关闭/结束
        self.end_session_requested.emit()
        self.close()


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
        # card.update_from_result({"status": status, "duration": duration})
        print(f"Mock update: {status}")

    timer = QtCore.QTimer()
    timer.timeout.connect(mock_update)
    timer.start(3000)

    bg_window.show()

    sys.exit(app.exec())
