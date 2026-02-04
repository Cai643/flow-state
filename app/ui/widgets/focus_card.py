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
        
        # 疲劳阈值默认值 (2700s = 45min)
        self.fatigue_threshold = 2700

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
                background-color: #fff5cf;
                border-radius: 12px;
                padding: 4px 12px;
                color: #4f6610;
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
        
        # 高级模式按钮
        self.advanced_btn = QtWidgets.QPushButton("⚙️ 高级模式")
        self.advanced_btn.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.advanced_btn.setFixedHeight(30)
        self.advanced_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # 初始样式
        self.advanced_btn.setStyleSheet("""
            QPushButton {
                background-color: #789035;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a8030;
            }
        """)
        self.advanced_btn.clicked.connect(self._on_advanced_mode_clicked)
        
        mode_layout.addWidget(self.advanced_btn)
        mode_container.setFixedHeight(30)
        
        # 高级设置面板 (初始隐藏)
        self.settings_panel = QtWidgets.QWidget()
        self.settings_panel.setVisible(False)
        settings_layout = QtWidgets.QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(15, 10, 15, 10)
        settings_layout.setSpacing(12)
        
        # 1. 模式选择 (专注模式 / 充能模式) - 仿图1/图2的黄白长框风格
        mode_select_container = QtWidgets.QWidget()
        mode_select_layout = QtWidgets.QHBoxLayout(mode_select_container)
        mode_select_layout.setContentsMargins(0, 0, 0, 0)
        mode_select_layout.setSpacing(0)
        
        # 专注模式按钮 (左侧)
        self.focus_btn = QtWidgets.QPushButton("💪 专注模式")
        self.focus_btn.setCheckable(True)
        self.focus_btn.setChecked(True)
        self.focus_btn.setFixedHeight(30)
        self.focus_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.focus_btn.clicked.connect(self._on_focus_mode_clicked)
        
        # 充能模式按钮 (右侧)
        self.recharge_btn = QtWidgets.QPushButton("🔋 充能模式")
        self.recharge_btn.setCheckable(True)
        self.recharge_btn.setChecked(False)
        self.recharge_btn.setFixedHeight(30)
        self.recharge_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.recharge_btn.clicked.connect(self._on_recharge_mode_clicked)
        
        mode_select_layout.addWidget(self.focus_btn, 1)
        mode_select_layout.addWidget(self.recharge_btn, 1)
        
        settings_layout.addWidget(mode_select_container)
        
        # 2. 疲劳阈值设定
        threshold_layout = QtWidgets.QHBoxLayout()
        threshold_layout.setSpacing(10)
        
        threshold_label = QtWidgets.QLabel("疲劳阈值:")
        threshold_label.setStyleSheet("color: white; font-size: 14px;")
        
        self.threshold_combo = QtWidgets.QComboBox()
        self.threshold_combo.addItems(["无", "15分钟", "30分钟", "45分钟 (默认)", "自定义..."])
        self.threshold_combo.setCurrentIndex(3) # 默认 45分钟
        self.threshold_combo.setEditable(True) # 允许编辑
        self.threshold_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert) # 不自动插入新项
        
        # 内部变量，用于存储自定义的值，以便在下拉列表中正确显示 "自定义..."
        self._custom_minutes = 45 
        
        # 连接 activated 信号以处理回车或选中
        # currentIndexChanged 在编辑文本时可能不会按预期触发，或者触发多次
        # 使用 lineEdit().editingFinished 处理自定义输入
        self.threshold_combo.lineEdit().editingFinished.connect(self._on_custom_input_finished)
        # 新增：实时监听文本变化，确保用户输入数字后立即生效，无需回车
        self.threshold_combo.editTextChanged.connect(self._on_custom_text_changed)
        self.threshold_combo.currentIndexChanged.connect(self._on_threshold_changed)

        # 仿图2风格：米黄色背景，圆角，文字颜色深棕色
        self.threshold_combo.setStyleSheet("""
            QComboBox {
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
                color: #5D4037; /* 文字深棕色 */
                background: #fff5cf; /* 背景米黄色 */
                font-size: 14px;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5D4037; /* 三角形箭头颜色深棕色 */
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background: #fff5cf;
                color: #5D4037;
                selection-background-color: #f0ebd0;
                border: none;
            }
        """)
        # self.threshold_combo.currentIndexChanged.connect(self._on_threshold_changed) # 移动到上面连接了
        
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_combo)
        threshold_layout.addStretch()
        settings_layout.addLayout(threshold_layout)
        
        settings_layout.addStretch() # 挤到上面
        
        # 3. 返回按钮 - 整个框框用高级设置的配色 (#789035)
        # 风格：实线边框，去掉虚线，文字改为 "回到实时监测面板"
        # 修改：文字颜色改为白色，背景色填充为橄榄绿
        
        self.back_btn = QtWidgets.QPushButton("🔙 回到实时监测面板")
        self.back_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.back_btn.setFixedHeight(36)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #789035; /* 橄榄绿背景 */
                color: white; /* 白色文字 */
                border: none; /* 无边框 */
                border-radius: 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a8030; /* 悬停加深 */
            }
        """)
        self.back_btn.clicked.connect(self._on_back_clicked)
        settings_layout.addWidget(self.back_btn)
        
        # 4. 初始化模式按钮样式 (需要在设置 current_mode 之后)
        # 移动到 _build_ui 的末尾，或者在这里临时设置一个默认值
        # 但 current_mode 是在 _build_ui 之后定义的，所以我们这里先不调用
        # self._update_mode_buttons_style() 

        # 121->128: 替换原有布局
        # 当前模式 (用于跟踪状态)
        self.current_mode = "focus"
        self._update_mode_buttons_style() # 这里调用是安全的

        # 主布局添加组件
        # 使用 QStackedLayout 或者简单的显隐控制
        # 这里为了简单，直接全部加上，通过 setVisible 控制
        self.dashboard_container = QtWidgets.QWidget()
        dashboard_layout = QtWidgets.QVBoxLayout(self.dashboard_container)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(6)
        
        dashboard_layout.addWidget(self.title_label)
        dashboard_layout.addSpacing(2)
        dashboard_layout.addWidget(self.status_label)
        dashboard_layout.addWidget(mode_container)
        
        layout.addWidget(self.dashboard_container)
        layout.addWidget(self.settings_panel)

    def reset_to_dashboard(self):
        self.settings_panel.setVisible(False)
        self.dashboard_container.setVisible(True)

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
        # 修改：充电模式下显示橄榄绿，专注模式下显示橄榄绿 (统一背景色)
        bg_color = QtGui.QColor("#7FA10F")
        bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 255)"
        
        # 修改：去除边框 (将边框颜色设置为透明或与背景一致)
        # border_color = QtGui.QColor("#7FA10F")
        # border_rgba = f"rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 255)"
        border_rgba = "transparent" # 去掉外框白线

        text_color = "#5D4037"
        
        # 悬停时... (如果需要边框反馈，可以在这里加回，但用户要求去掉白线，我们暂时全部去掉)
        if self.hovering:
             # border_color = border_color.lighter(110)
             # border_rgba = f"rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 255)"
             pass

        style = """
            QWidget {
                background-color: %s;
                border-radius: 16px;
                border: 0px solid transparent; 
                color: %s;
            }
        """
        self.setStyleSheet(style % (bg_rgba, text_color))

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
            # 专注模式：橄榄绿底白字
            self.focus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #789035;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6a8030;
                }
            """)
            # 充电模式：米黄底深绿字
            self.recharge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fff5cf;
                    color: #4f6610;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #f0ebd0;
                }
            """)
        else:
            # 专注模式：米黄底深绿字
            self.focus_btn.setStyleSheet("""
                QPushButton {
                    background-color: #fff5cf;
                    color: #4f6610;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    background-color: #f0ebd0;
                }
            """)
            # 充电模式：橙色底白字 (区分模式)
            self.recharge_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFB74D;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #FFA726;
                }
            """)

    def _on_advanced_mode_clicked(self):
        """点击高级模式：切换到设置面板"""
        self.dashboard_container.setVisible(False)
        self.settings_panel.setVisible(True)
        # 调整大小以适应内容
        # self.adjustSize() 
        # 或者保持固定大小，看效果
        
    def _on_back_clicked(self):
        """点击返回：回到仪表盘"""
        self.settings_panel.setVisible(False)
        self.dashboard_container.setVisible(True)
        
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
            
    # 删除不再需要的 _on_mode_changed 方法 (因为它依赖 radio 按钮) 
            
    def _on_threshold_changed(self, index):
        """处理阈值变更 (下拉选择)"""
        # 映射 index 到 秒数
        # ["无", "15分钟", "30分钟", "45分钟 (默认)", "自定义..."]
        # index: 0=Disabled, 1=900s, 2=1800s, 3=2700s, 4=Custom
        
        # 检查是否选择了 "自定义..." (最后一个选项)
        if index == 4:
            # 选中 "自定义..." 时，清空文本框并聚焦，让用户输入
            # 获取当前自定义的分钟数，如果没有则默认为 45
            current_mins = getattr(self, '_custom_minutes', 45)
            
            # 使用 setInputMask 限制输入格式
            # "999 分钟; " : 9表示可选数字，分号后的空格表示占位符用空格代替下划线
            self.threshold_combo.lineEdit().setInputMask("999 分钟; ")
            
            # 设置显示文本 (注意要匹配 mask 格式，数字靠右或靠左取决于实现，通常简单设置即可)
            # 为了美观，我们可能希望数字靠左，但 mask 通常是固定宽度的
            # 尝试直接设置文本，Qt 会自动适配 mask
            self.threshold_combo.lineEdit().setText(f"{current_mins}")
            
            # 选中数字部分
            self.threshold_combo.lineEdit().setSelection(0, len(str(current_mins)))
            
            self.threshold_combo.lineEdit().setFocus()
            return

        # 非自定义模式，清除掩码
        self.threshold_combo.lineEdit().setInputMask("")
        
        threshold_map = {
            0: 0,    # 无 (关闭)
            1: 900,  # 15min
            2: 1800, # 30min
            3: 2700  # 45min
        }
        seconds = threshold_map.get(index, 2700)
        self.fatigue_threshold = seconds
        
        # 如果切换回其他选项，需要把最后一项的文本重置为 "自定义..."
        if self.threshold_combo.itemText(4) != "自定义...":
            self.threshold_combo.setItemText(4, "自定义...")

    def _on_custom_text_changed(self, text):
        """实时处理自定义输入文本变化"""
        # 只有在 index 为 4 (自定义) 时才处理
        if self.threshold_combo.currentIndex() != 4:
            return

        # 尝试提取数字并更新阈值
        import re
        match = re.search(r'(\d+)', text)
        if match:
            try:
                minutes = int(match.group(1))
                # 限制范围 1-120 (这里只更新内部值，不修改界面显示，以免打断输入)
                minutes = max(1, min(minutes, 120))
                
                # 实时更新阈值
                seconds = minutes * 60
                self.fatigue_threshold = seconds
                self._custom_minutes = minutes
                
                # print(f"[DEBUG] Real-time threshold update: {minutes} mins ({seconds}s)")
            except ValueError:
                pass

    def _on_custom_input_finished(self):
        """处理自定义输入完成 (回车或失焦)"""
        # 只有在 index 为 4 (自定义) 时才处理
        if self.threshold_combo.currentIndex() != 4:
            return

        text = self.threshold_combo.currentText().strip()
        
        # 如果文本为空，不做处理
        if not text:
            return

        # 尝试提取数字
        # 支持格式: "20", "20分钟", "20m" 等
        import re
        match = re.search(r'(\d+)', text)
        if match:
            minutes = int(match.group(1))
            # 限制范围 1-120
            minutes = max(1, min(minutes, 120))
            
            self._custom_minutes = minutes # 记住这个值
            
            seconds = minutes * 60
            self.fatigue_threshold = seconds
            
            # 格式化显示: "X 分钟" (注意中间有空格)
            display_text = f"{minutes} 分钟"
            
            # 下拉列表里始终显示 "自定义..."
            self.threshold_combo.blockSignals(True)
            self.threshold_combo.setItemText(4, "自定义...")
            self.threshold_combo.setCurrentIndex(4)
            self.threshold_combo.blockSignals(False)
            
            # 关键：强制设置 lineEdit 文本为 "X 分钟"
            if self.threshold_combo.lineEdit():
                # 保持掩码，确保格式一致 ("999 分钟; ")
                # 注意：setText 时只需设置数字部分，掩码会自动补充 " 分钟"
                self.threshold_combo.lineEdit().setInputMask("999 分钟; ")
                self.threshold_combo.lineEdit().setText(str(minutes))
                self.threshold_combo.lineEdit().clearFocus()
        else:
            # 输入无效的处理...
            # 如果是 "自定义..." 或者包含 "分钟" 但没数字 (可能是刚切换过来的状态)，保持原状
            # 注意：有了掩码后，text 可能会包含空格和掩码字符
            # 比如 "   分钟"
            if "分钟" in text and not any(c.isdigit() for c in text):
                 return
            
            # 其他情况恢复默认
            # 清除掩码以便显示普通文本
            if self.threshold_combo.lineEdit():
                self.threshold_combo.lineEdit().setInputMask("")
            self.threshold_combo.setCurrentIndex(3)
            
    def _handle_custom_threshold(self):
        """已废弃，改用直接输入"""
        pass

    # 对外数据更新接口：联动监控结果
    def update_from_result(self, result: dict):
        # 1. 解析实时监控数据
        current_status = result.get("status", "focus")
        current_duration = result.get("duration", 0) # 秒
        
        # 2. 查询今日累计数据 (调用 StatsDAO)
        try:
            from app.data.dao.activity_dao import StatsDAO
            from datetime import date
            try:
                StatsDAO.recompute_today_from_sessions()
            except Exception:
                pass
            summary = StatsDAO.get_daily_summary(date.today())
            total_focus_sec = int((summary or {}).get('total_focus_time') or 0)
            if current_status in ['work', 'focus']:
                total_focus_sec += int(current_duration or 0)
            display_focus_hours = total_focus_sec / 3600.0
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

        # 4. 检查是否需要显示娱乐提醒 (Fatigue Dialog)
        # 逻辑：
        # - 只有在“专注模式”下才提醒
        # - 当前状态是 entertainment
        # - 持续时间超过阈值 (例如 15分钟 = 900秒，或者 30秒测试用)
        # - 没有已经显示的弹窗 (由 main.py 或 signals 控制，这里只是发射信号)
        
        # 从 result 中获取 current_activity_duration
        current_activity_duration = result.get("current_activity_duration", 0)
        
        # 动态获取阈值 (默认为 900秒 / 15分钟)
        # 注意：这里是娱乐阈值，现在 UI 控制的是疲劳阈值，所以娱乐阈值固定为 900
        threshold = 900
        
        # 阈值设置 (测试用 30秒，实际建议 15分钟)
        # REMINDER_THRESHOLD = 30 
        
        if self.current_mode == "focus":
            if current_status == 'entertainment' and current_activity_duration >= threshold:
                # 只有当上次还没达到阈值，这次刚达到时，才发射信号 (避免重复发射)
                # 或者依靠外部逻辑去重。这里我们简单处理：只要满足条件就检查是否已发射
                pass 
                # 注意：这里的逻辑其实更适合放在 main.py 中统一处理，因为弹窗是全局的。
                # FocusCard 主要是展示数据。
                # 但为了响应用户的"点击充电模式关闭提醒"，我们需要确保 main.py 能感知到当前模式。
                # main.py 可以通过读取 FocusCard.current_mode 或者 ActivityHistoryManager.get_current_mode() 来判断。
        
        target_hours = 8.0
        self.title_label.setText(
            f"🎯 今日专注  {display_focus_hours:.1f}h / {target_hours:.0f}h")

        # 修改：使用当前状态的持续时间，而不是总的 current_duration
        # 这里的 result['current_window_duration'] 可能不存在，我们需要检查 thread.py 传递了什么
        # 之前我们在 thread.py 中添加了 current_window_duration 字段
        
        # 实际上，current_duration 已经是总持续时间了 (time.time() - status_start_time)
        # 所以直接用 current_duration 显示 "已连续XX分钟" 是对的
        display_minutes = int(current_duration / 60)
        
        # 针对娱乐状态的特殊显示：使用 current_activity_duration
        if current_status == 'entertainment':
             # 娱乐状态下，我们想看看到底“摸鱼”了多久
             entertainment_minutes = int(current_activity_duration / 60)
             display_minutes = entertainment_minutes

        # efficiency_gain = 30 # 暂时保留模拟值，后续可改为基于算法计算
        
        # 简单算法：每拉回一次，效率提升 5%，上限 50%
        efficiency_gain = min(self.pull_back_count * 5, 50)
        
        display_pull_back_count = self.pull_back_count

        if self.current_mode == "recharge":
            # 充电模式下，无论什么状态都显示充电中
            # 如果实际是娱乐，也可以显示娱乐了多久，这里我们统一显示已连续多久（即 display_minutes）
            self.status_label.setText(f"🔋 充电中  已连续{display_minutes}分钟")
        else:
            if current_status == 'entertainment':
                 self.status_label.setText(f"🍿 娱乐中  已连续{display_minutes}分钟")
            elif current_status in ['work', 'focus']:
                 self.status_label.setText(f"⚡ 专注中  已连续{display_minutes}分钟")
            else:
                 self.status_label.setText(f"⏸️ 休息中  已连续{display_minutes}分钟")


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
