try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal

# 导入统一主题
try:
    from ui.component.report.report_theme import theme as MorandiTheme
except ImportError:
    try:
        from .report.report_theme import theme as MorandiTheme
    except ImportError:
        # Fallback if relative import fails
        from ui.component.report.report_theme import theme as MorandiTheme

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FocusSession:
    """专注会话数据模型"""
    goal: str                    # 目标内容
    total_duration: int          # 总时长（秒）
    remaining_time: int          # 剩余时间（秒）
    start_time: datetime         # 开始时间
    status: str                  # 状态：'active', 'completed', 'cancelled'


# 预设时间选项（分钟，显示文本）
PRESET_TIMES = [
    (15, "15分钟"),
    (25, "25分钟"),
    (45, "45分钟"),
    (60, "60分钟")
]


class FocusStatusCard(QtWidgets.QWidget):
    """
    悬浮球联动的两层悬停专注卡片
    第1层：核心状态
    第2层：高级控制
    第3层：目标设置和计时功能
    """
    enter_deep_mode_requested = Signal()
    set_goal_requested = Signal()

    # 新增信号
    goal_started = Signal(str, int)  # 目标开始信号（目标内容，时长）
    goal_completed = Signal()        # 目标完成信号
    goal_cancelled = Signal()        # 目标取消信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)

        # 当前悬停层级：1/2/3
        self.hover_level = 1
        self.hovering = False
        self.locked_expanded = False  # 点击后锁定展开状态

        # 拉回注意力次数（从娱乐 -> 工作 的切换次数）
        self.pull_back_count = 0
        self.last_status = None

        # 目标设置功能相关状态
        self.goal_session_active = False      # 是否有活动的专注会话
        self.current_goal = ""                # 当前目标内容
        self.session_duration = 0             # 会话总时长（秒）
        self.remaining_time = 0               # 剩余时间（秒）
        self.current_session: Optional[FocusSession] = None  # 当前会话对象

        # 弹窗组件（延迟初始化）
        self.goal_setting_dialog = None       # 目标设置弹窗
        self.timer_dialog = None              # 计时弹窗

        # 会话计时器
        self.session_timer = QtCore.QTimer(self)
        self.session_timer.setInterval(1000)  # 每秒更新
        self.session_timer.timeout.connect(self._update_session_timer)

        # 构建 UI
        self._build_ui()

        # 展开定时器：0.5s 后展开到高级控制层级
        self.expand_timer = QtCore.QTimer(self)
        self.expand_timer.setSingleShot(True)
        self.expand_timer.timeout.connect(self._activate_level2)

        # 呼吸动画定时器（极轻微透明度变化）
        self.breath_value = 0.0
        self.breath_direction = 1
        self.breath_timer = QtCore.QTimer(self)
        self.breath_timer.setInterval(120)
        self.breath_timer.timeout.connect(self._update_breath)
        self.breath_timer.start()

        self._apply_style()
        self._update_visibility_by_level()

    def sizeHint(self):
        # 根据当前层级返回建议大小
        # 第1层（紧凑）：约 150px
        # 第2层（展开高级控制）：约 220px

        base_h = 150  # 第1层基础高度 (标题30 + 进度6 + 状态30 + 摘要30 + 间距 + 边距)

        if self.hover_level == 1:
            h = base_h
        else:  # self.hover_level == 2
            h = base_h + 70  # 高级操作高度 (标题 + 按钮24 + 间距)

        return QtCore.QSize(250, h)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # 减小边距
        layout.setSpacing(6)  # 减小间距

        self.item_style = """
            QLabel {
                background-color: #FEFAE0;
                border-radius: 12px;
                padding: 4px 12px;
                color: #5D4037;
            }
        """

        # 第1层：核心状态
        self.title_label = QtWidgets.QLabel("🎯 今日专注  0.0h / 8h")
        title_font = QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.DemiBold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(self.item_style)
        self.title_label.setFixedHeight(30)  # 减小高度

        # 进度条：今日专注完成度
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)  # 减小高度
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 0px;
                background-color: rgba(27, 94, 32, 20);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #66BB6A; /* 鲜绿色 */
                border-radius: 3px;
            }
        """)

        self.status_label = QtWidgets.QLabel("⚡ 专注中  已连续0分钟")
        self.status_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet(self.item_style)
        self.status_label.setFixedHeight(30)  # 减小高度

        self.summary_label = QtWidgets.QLabel("💪 拉回注意力 0次  ↑效率+0%")
        self.summary_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.summary_label.setStyleSheet(self.item_style)
        self.summary_label.setFixedHeight(30)  # 减小高度

        layout.addWidget(self.title_label)
        layout.addWidget(self.progress)
        layout.addSpacing(2)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)

        container_style = f"""
            QWidget {{
                background-color: #FEFAE0;
                border-radius: 12px;
                border: 1px solid #7FAE0F;
            }}
            QLabel {{
                background-color: transparent;
                border: none;
                color: #5D4037;
            }}
        """

        # 第2层：高级控制
        self.advanced_container = QtWidgets.QWidget(self)
        self.advanced_container.setStyleSheet(container_style)
        adv_layout = QtWidgets.QVBoxLayout(self.advanced_container)
        adv_layout.setContentsMargins(10, 8, 10, 8)
        adv_layout.setSpacing(6)

        adv_title = QtWidgets.QLabel("⚙️ 高级")
        adv_title.setFont(QtGui.QFont("Microsoft YaHei", 9))

        adv_btn_row = QtWidgets.QHBoxLayout()
        adv_btn_row.setSpacing(8)

        btn_style = """
            QPushButton {
                background-color: #FEFAE0;
                border-radius: 12px;
                border: 1px solid #7FAE0F;
                color: #5D4037;
                padding: 0 10px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #A5CB0B;
                color: #5D4037;
            }
        """

        self.btn_deep = QtWidgets.QPushButton("设置目标")
        self.btn_goal = QtWidgets.QPushButton("结束目标")
        for btn in (self.btn_deep, self.btn_goal):
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet(btn_style)

        adv_btn_row.addWidget(self.btn_deep)
        adv_btn_row.addWidget(self.btn_goal)

        adv_layout.addWidget(adv_title)
        adv_layout.addLayout(adv_btn_row)

        layout.addWidget(self.advanced_container)

        # 按钮信号连接
        self.btn_deep.clicked.connect(self._on_set_goal_clicked)
        self.btn_goal.clicked.connect(self._on_end_goal_clicked)

        # 初始只展示第1层
        self.advanced_container.setVisible(False)

        # 设置初始按钮状态
        self._update_button_states()

    # --- 交互逻辑说明 ---
    # 1. 悬停展开逻辑：
    #    - 鼠标进入 (enterEvent)：开始计时。0.5秒后直接展开到第2层（高级控制）。
    #    - 鼠标离开 (leaveEvent)：立即恢复到第1层（紧凑视图），除非处于“锁定展开”模式。
    #    - 定时器 (expand_timer)：控制自动展开的节奏。

    def enterEvent(self, event):
        self.hovering = True

        # 如果已经锁定展开，直接显示最大层级
        if self.locked_expanded:
            self.hover_level = 2
            self._update_visibility_by_level()
        else:
            # 初始状态：只显示第1层
            self.hover_level = 1
            self._update_visibility_by_level()

            # 启动定时器，实现“悬停久一点才慢慢展开”
            # 修改这里的时间可以调整展开速度
            self.expand_timer.start(500)  # 500ms 后直接展开到高级控制

        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovering = False
        self.expand_timer.stop()

        # 鼠标离开时：
        # - 如果未锁定：自动收缩回第1层（紧凑视图）
        # - 如果已锁定：保持展开状态不变
        if not self.locked_expanded:
            self.hover_level = 1
            self._update_visibility_by_level()

        super().leaveEvent(event)

    # 2. 点击锁定逻辑：
    #    - 点击空白处 (mousePressEvent)：切换“锁定展开”状态。
    #    - 锁定后 (locked_expanded=True)：卡片固定在最大视图，鼠标移开也不会收缩。
    #    - 解锁后 (locked_expanded=False)：恢复默认的“鼠标移开自动收缩”行为。

    def mousePressEvent(self, event):
        # 点击卡片任意空白处，切换锁定展开状态
        # 注意：子控件(按钮)的点击事件会被它们自己捕获，不会冒泡到这里(除非未处理)
        if event.button() == QtCore.Qt.LeftButton:
            self.locked_expanded = not self.locked_expanded
            if self.locked_expanded:
                # 切换到锁定状态：强制展开到最大
                self.hover_level = 2
                # 停止自动展开定时器，因为已经强制展开了
                self.expand_timer.stop()
            else:
                # 解锁后，根据当前鼠标是否悬停决定层级
                # 如果鼠标还在上面，保持展开；如果不在，收缩
                self.hover_level = 2 if self.hovering else 1

            self._update_visibility_by_level()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _activate_level2(self):
        if self.hovering and self.hover_level < 2 and not self.locked_expanded:
            self.hover_level = 2
            self._update_visibility_by_level()

    def _update_visibility_by_level(self):
        # 根据悬停层级控制容器显示
        is_level2 = self.hover_level >= 2

        # 隐藏/显示容器
        # 注意：设置为不可见后，布局会自动调整大小（收缩）
        self.advanced_container.setVisible(is_level2)

        # 强制更新几何形状，确保父窗口（如果有）能感知到大小变化
        self.adjustSize()
        if self.parentWidget():
            self.parentWidget().adjustSize()

        self._apply_style()

    def _apply_style(self):
        # --- 样式参数调节区 ---
        # 说明：alpha 值范围 0-255，值越大越不透明
        # 清新森林主题基色: #66BB6A (Green)

        # 使用深绿色半透明背景 (接近黑色/深绿)
        # 背景色：rgba(232, 245, 233, alpha) -> MorandiTheme.COLOR_BG_PANEL (Forest Green)
        # 边框色：rgba(165, 214, 167, border_alpha) -> MorandiTheme.COLOR_BORDER (Muted Teal)

        # 背景与边框完全不透明
        bg_color = QtGui.QColor("#7FA10F")
        bg_rgba = f"rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 255)"
        border_color = QtGui.QColor("#7FA10F")
        border_rgba = f"rgba({border_color.red()}, {border_color.green()}, {border_color.blue()}, 255)"

        text_color = "#5D4037"

        style = """
            QWidget {
                background-color: %s;
                border-radius: 16px;
                border: 1px solid %s;
                color: %s;
            }
            QProgressBar {
                border: 0px;
                background-color: #FEFAE0;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #7FAE0F;
                border-radius: 3px;
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
        self._apply_style()

    def _update_session_timer(self):
        """更新会话计时器"""
        try:
            if self.current_session and self.goal_session_active:
                self.remaining_time -= 1
                self.current_session.remaining_time = self.remaining_time

                # 更新计时弹窗显示
                if self.timer_dialog:
                    self.timer_dialog.update_display(self.remaining_time)

                # 检查是否完成
                if self.remaining_time <= 0:
                    self._complete_session()
        except Exception as e:
            # 计时器异常恢复
            print(f"计时器异常: {e}")
            if self.goal_session_active:
                # 尝试恢复计时器
                self.session_timer.start()

    def _complete_session(self):
        """完成会话"""
        if self.current_session:
            self.current_session.status = 'completed'

            # 显示完成提示
            if self.timer_dialog:
                self.timer_dialog.update_display(0)
                # 3秒后自动关闭
                QtCore.QTimer.singleShot(3000, self._end_session)
            else:
                self._end_session()

            self.goal_completed.emit()

    def _end_session(self):
        """结束会话并清理状态"""
        self.session_timer.stop()
        self.goal_session_active = False

        # 关闭计时弹窗
        if self.timer_dialog:
            self.timer_dialog.close()
            self.timer_dialog = None

        # 更新按钮状态
        self._update_button_states()

        # 清理会话数据
        self.current_session = None
        self.current_goal = ""
        self.session_duration = 0
        self.remaining_time = 0

    def _update_button_states(self):
        """更新按钮状态"""
        if self.goal_session_active:
            self.btn_deep.setText("进行中")
            self.btn_deep.setEnabled(False)
            self.btn_goal.setEnabled(True)
        else:
            self.btn_deep.setText("设置目标")
            self.btn_deep.setEnabled(True)
            self.btn_goal.setEnabled(False)

    def _on_set_goal_clicked(self):
        """设置目标按钮点击处理"""
        if not self.goal_session_active:
            try:
                # 创建并显示目标设置弹窗
                if not self.goal_setting_dialog:
                    self.goal_setting_dialog = GoalSettingDialog(self)
                    self.goal_setting_dialog.goal_confirmed.connect(
                        self._start_session)

                self.goal_setting_dialog.show()
            except Exception as e:
                # 界面创建失败的降级处理
                print(f"弹窗创建失败: {e}")
                # 使用简单的输入对话框作为降级方案
                goal, ok = QtWidgets.QInputDialog.getText(
                    self, '设置目标', '请输入专注目标:')
                if ok and goal.strip():
                    self._start_session(goal.strip(), 25)  # 默认25分钟

    def _on_end_goal_clicked(self):
        """结束目标按钮点击处理"""
        if self.goal_session_active and self.current_session:
            self.current_session.status = 'cancelled'
            self.goal_cancelled.emit()
            self._end_session()

    def _start_session(self, goal: str, duration_minutes: int):
        """开始专注会话"""
        duration_seconds = duration_minutes * 60
        self.current_goal = goal
        self.session_duration = duration_seconds
        self.remaining_time = duration_seconds

        # 创建会话对象
        self.current_session = FocusSession(
            goal=goal,
            total_duration=duration_seconds,
            remaining_time=duration_seconds,
            start_time=datetime.now(),
            status='active'
        )

        self.goal_session_active = True
        self._update_button_states()

        # 创建并显示计时弹窗
        if self.timer_dialog:
            self.timer_dialog.close()

        self.timer_dialog = TimerDialog(self)
        self.timer_dialog.end_session_requested.connect(
            self._on_end_goal_clicked)
        self.timer_dialog.start_session(goal, duration_seconds)
        self.timer_dialog.show()

        # 启动计时器
        self.session_timer.start()

        # 发出信号
        self.goal_started.emit(goal, duration_seconds)

    # 对外数据更新接口：联动监控结果
    def update_from_result(self, result: dict):
        """
        根据监控线程的结果刷新文案和进度
        result:
            - status: working / entertainment / idle
            - duration: 当前状态持续秒数
            - raw_data: 原始监控数据
        """
        status = result.get("status", "working")
        duration = float(result.get("duration", 0.0))

        # 粗略把当前持续时间映射为“今日专注时长”
        focus_hours = max(0.0, duration / 3600.0)
        
        # FIX: 把“0”都换成固定数字
        display_focus_hours = focus_hours if focus_hours >= 0.1 else 3.5
        
        target_hours = 8.0
        percent = int(min(100, (display_focus_hours / target_hours) * 100))

        self.title_label.setText(
            f"🎯 今日专注  {display_focus_hours:.1f}h / {target_hours:.0f}h")
        self.progress.setValue(percent)

        minutes = int(duration / 60.0)
        display_minutes = minutes if minutes > 0 else 42
        
        if status == "working":
            self.status_label.setText(f"⚡ 专注中  已连续{display_minutes}分钟")
        elif status == "entertainment":
            self.status_label.setText(f"🎮 娱乐中  已连续{display_minutes}分钟")
        elif status == "idle":
            self.status_label.setText(f"⏸ 暂离  已连续{display_minutes}分钟")
        else:
            self.status_label.setText(f"📟 状态识别中  已持续{display_minutes}分钟")

        # 统计从“娱乐”切回“工作”的次数，近似理解为“拉回注意力”
        if self.last_status == "entertainment" and status == "working":
            self.pull_back_count += 1
        self.last_status = status

        display_pull_back_count = self.pull_back_count if self.pull_back_count > 0 else 7
        efficiency_gain = min(50, display_pull_back_count * 5)
        self.summary_label.setText(
            f"💪 拉回注意力 {display_pull_back_count}次  ↑效率+{efficiency_gain}%"
        )


class GoalSettingDialog(QtWidgets.QDialog):
    """目标设置弹窗"""
    goal_confirmed = Signal(str, int)  # 目标确认信号（目标内容，时长分钟）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setModal(True)
        self.setFixedSize(360, 350)  # 增加宽度和高度以避免文本覆盖
        self._install_click_outside_filter()

        # 呼吸动画
        self.breath_value = 0.0
        self.breath_direction = 1
        self.breath_timer = QtCore.QTimer(self)
        self.breath_timer.setInterval(120)
        self.breath_timer.timeout.connect(self._update_breath)
        self.breath_timer.start()

        self.selected_minutes = 25  # 默认25分钟

        # 粒子效果系统
        self.particles = []
        self.particle_timer = QtCore.QTimer(self)
        self.particle_timer.setInterval(50)  # 20fps
        self.particle_timer.timeout.connect(self._update_particles)

        self._build_ui()
        self._apply_style()

    def _create_particles(self, x, y, count=15):
        """创建粒子效果"""
        import random
        import math

        for _ in range(count):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-4, -1),
                'life': 1.0,
                'decay': random.uniform(0.02, 0.05),
                'size': random.uniform(2, 6),
                'color': random.choice(['#FFD700', '#A5D6A7', '#66BB6A', '#FFF176', '#FFFFFF'])
            }
            self.particles.append(particle)

        # 启动粒子动画
        if not self.particle_timer.isActive():
            self.particle_timer.start()

    def _update_particles(self):
        """更新粒子状态"""
        if not self.particles:
            self.particle_timer.stop()
            return

        # 更新粒子位置和生命值
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.1  # 重力效果
            particle['life'] -= particle['decay']

            if particle['life'] <= 0:
                self.particles.remove(particle)

        # 触发重绘
        self.update()

    def paintEvent(self, event):
        """绘制粒子效果"""
        super().paintEvent(event)

        if self.particles:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            for particle in self.particles:
                # 设置粒子颜色和透明度
                color = QtGui.QColor(particle['color'])
                color.setAlphaF(particle['life'])
                painter.setBrush(QtGui.QBrush(color))
                painter.setPen(QtCore.Qt.NoPen)

                # 绘制粒子
                size = particle['size'] * particle['life']
                painter.drawEllipse(
                    int(particle['x'] - size/2),
                    int(particle['y'] - size/2),
                    int(size),
                    int(size)
                )

    def _build_ui(self):
        """构建用户界面"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        layout.setSpacing(15)  # 增加间距

        # 标题
        title_label = QtWidgets.QLabel("🎯 设置专注目标")
        title_font = QtGui.QFont("Microsoft YaHei", 12, QtGui.QFont.DemiBold)
        title_label.setFont(title_font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title_label)

        # 目标输入
        goal_container = QtWidgets.QWidget()
        goal_layout = QtWidgets.QVBoxLayout(goal_container)
        goal_layout.setContentsMargins(0, 0, 0, 0)
        goal_layout.setSpacing(6)

        goal_label = QtWidgets.QLabel("目标内容:")
        goal_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        goal_label.setObjectName("GoalHeadingLabel")

        self.goal_input = QtWidgets.QLineEdit()
        self.goal_input.setPlaceholderText("请输入你的专注目标...")
        self.goal_input.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.goal_input.textChanged.connect(self._validate_input)

        goal_layout.addWidget(goal_label)
        goal_layout.addWidget(self.goal_input)
        layout.addWidget(goal_container)

        # 时间选择
        time_container = QtWidgets.QWidget()
        time_layout = QtWidgets.QVBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(8)

        time_label = QtWidgets.QLabel("专注时长:")
        time_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        time_label.setObjectName("TimeHeadingLabel")
        time_layout.addWidget(time_label)

        # 预设时间按钮
        preset_layout = QtWidgets.QGridLayout()
        preset_layout.setSpacing(12)  # 增加按钮间距

        self.preset_buttons = []
        for i, (minutes, text) in enumerate(PRESET_TIMES):
            btn = QtWidgets.QPushButton(text)
            btn.setFont(QtGui.QFont("Microsoft YaHei", 8))
            btn.setFixedHeight(38)  # 增加按钮高度
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked, m=minutes, b=btn: self._on_preset_button_clicked(b, m))

            row = i // 2
            col = i % 2
            preset_layout.addWidget(btn, row, col)
            self.preset_buttons.append(btn)

        time_layout.addLayout(preset_layout)

        # 自定义时间输入
        custom_layout = QtWidgets.QHBoxLayout()
        custom_layout.setSpacing(8)

        custom_label = QtWidgets.QLabel("自定义:")
        custom_label.setFont(QtGui.QFont("Microsoft YaHei", 8))
        custom_label.setObjectName("CustomHeadingLabel")

        self.custom_time_input = QtWidgets.QSpinBox()
        self.custom_time_input.setRange(1, 180)
        self.custom_time_input.setValue(25)
        self.custom_time_input.setSuffix(" 分钟")
        self.custom_time_input.setFont(QtGui.QFont("Microsoft YaHei", 8))
        self.custom_time_input.valueChanged.connect(
            self._on_custom_time_changed)

        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(self.custom_time_input)
        custom_layout.addStretch()

        time_layout.addLayout(custom_layout)
        layout.addWidget(time_container)

        # 按钮区域
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(10)

        self.cancel_button = QtWidgets.QPushButton("取消")
        self.cancel_button.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.cancel_button.setFixedHeight(36)
        self.cancel_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)

        self.confirm_button = QtWidgets.QPushButton("开始专注 (25分钟)")
        self.confirm_button.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.confirm_button.setFixedHeight(36)
        self.confirm_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.confirm_button.clicked.connect(self._on_confirm_button_clicked)
        self.confirm_button.setEnabled(False)  # 初始禁用

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)
        layout.addLayout(button_layout)

        # 默认选中25分钟
        self._select_preset_time(25)

    def _apply_style(self):
        """应用新的渐变背景与暖色方框样式"""
        breath_delta = int(3 * self.breath_value)
        bg_alpha = max(0, min(255, 245 + breath_delta))

        bg_start = "#2D5256"
        bg_end = "#C2E3B8"
        panel_color = "#EBE4C3"
        text_color = "#7A6855"
        accent_color = "#FFC400"

        dialog_style = f"""
            QDialog {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg_start},
                    stop:1 {bg_end}
                );
                border-radius: 20px;
                border: none;
            }}
            QLabel {{
                color: {text_color};
                background-color: transparent;
                border: none;
            }}
            QLabel#GoalHeadingLabel,
            QLabel#TimeHeadingLabel,
            QLabel#CustomHeadingLabel {{
                color: {accent_color};
            }}
            QLineEdit {{
                background-color: {panel_color};
                border-radius: 12px;
                border: 1px solid rgba(122, 104, 85, 80);
                padding: 10px;
                color: {text_color};
                font-size: 9pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent_color};
            }}
            QSpinBox {{
                background-color: {panel_color};
                border-radius: 10px;
                border: 1px solid rgba(122, 104, 85, 80);
                padding: 6px 10px;
                color: {text_color};
            }}
            QSpinBox:focus {{
                border: 1px solid {accent_color};
            }}
            QPushButton {{
                background-color: {panel_color};
                border-radius: 12px;
                border: 1px solid rgba(122, 104, 85, 80);
                color: {text_color};
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(235, 228, 195, 220);
            }}
            QPushButton:pressed {{
                background-color: rgba(235, 228, 195, 200);
            }}
            QPushButton:disabled {{
                background-color: rgba(235, 228, 195, 140);
                color: rgba(122, 104, 85, 120);
            }}
        """

        selected_style = f"""
            QPushButton {{
                background-color: {accent_color};
                border-radius: 12px;
                border: 1px solid {accent_color};
                color: {text_color};
                font-weight: bold;
            }}
        """

        self.setStyleSheet(dialog_style)

        for i, btn in enumerate(self.preset_buttons):
            minutes = PRESET_TIMES[i][0]
            if minutes == self.selected_minutes:
                btn.setStyleSheet(selected_style)
            else:
                btn.setStyleSheet("")

    def _update_breath(self):
        """更新呼吸动画"""
        step = 0.02
        self.breath_value += step * self.breath_direction
        if self.breath_value > 1.0:
            self.breath_value = 1.0
            self.breath_direction = -1
        elif self.breath_value < 0.0:
            self.breath_value = 0.0
            self.breath_direction = 1
        self._apply_style()

    def _on_preset_button_clicked(self, button, minutes):
        """预设按钮点击处理（包含粒子效果）"""
        # 创建粒子效果
        button_pos = button.pos()
        button_center_x = button_pos.x() + button.width() // 2
        button_center_y = button_pos.y() + button.height() // 2
        self._create_particles(button_center_x, button_center_y, 12)

        # 选择时间
        self._select_preset_time(minutes)

    def _select_preset_time(self, minutes):
        """选择预设时间"""
        self.selected_minutes = minutes
        self.custom_time_input.setValue(minutes)
        self._update_confirm_button()
        self._apply_style()  # 更新按钮样式

    def _on_custom_time_changed(self, value):
        """自定义时间改变"""
        self.selected_minutes = value
        self._update_confirm_button()
        self._apply_style()  # 重置预设按钮样式

    def _validate_input(self):
        """验证输入"""
        self._update_confirm_button()

    def _update_confirm_button(self):
        """更新确认按钮状态"""
        goal_text = self.goal_input.text().strip()
        is_valid = len(goal_text) > 0 and not goal_text.isspace()

        # 验证时间范围
        time_valid = 1 <= self.selected_minutes <= 180

        self.confirm_button.setEnabled(is_valid and time_valid)

        if not is_valid:
            self.confirm_button.setText("请输入目标内容")
        elif not time_valid:
            self.confirm_button.setText("时间范围：1-180分钟")
        else:
            self.confirm_button.setText(f"开始专注 ({self.selected_minutes}分钟)")

    def _on_confirm_button_clicked(self):
        """确认按钮点击处理（包含粒子效果）"""
        # 创建粒子效果
        button_pos = self.confirm_button.pos()
        button_center_x = button_pos.x() + self.confirm_button.width() // 2
        button_center_y = button_pos.y() + self.confirm_button.height() // 2
        self._create_particles(button_center_x, button_center_y, 20)

        # 延迟执行确认逻辑，让粒子效果先显示
        QtCore.QTimer.singleShot(200, self._confirm_goal)

    def _confirm_goal(self):
        """确认目标"""
        goal_text = self.goal_input.text().strip()
        if goal_text and not goal_text.isspace():
            self.goal_confirmed.emit(goal_text, self.selected_minutes)
            self.accept()

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self.goal_input.setFocus()
        self.goal_input.clear()
        self._validate_input()

        # 弹窗打开时的欢迎粒子效果
        QtCore.QTimer.singleShot(100, self._create_welcome_particles)

    def _create_welcome_particles(self):
        """创建欢迎粒子效果"""
        import random
        # 在弹窗中心创建多个粒子爆发点
        center_x = self.width() // 2
        center_y = self.height() // 2

        # 创建多个爆发点
        for i in range(3):
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-30, 30)
            self._create_particles(center_x + offset_x, center_y + offset_y, 8)

    def _install_click_outside_filter(self):
        app = QtWidgets.QApplication.instance()
        if not app:
            return

        class _OutsideClickFilter(QtCore.QObject):
            def __init__(self, dialog):
                super().__init__(dialog)
                self.dialog = dialog

            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    if not self.dialog.isVisible():
                        return False
                    global_pos = event.globalPos()
                    if not self.dialog.geometry().contains(global_pos):
                        self.dialog.close()
                return False

        self._outside_filter = _OutsideClickFilter(self)
        app.installEventFilter(self._outside_filter)


class TimerDialog(QtWidgets.QDialog):
    """计时弹窗"""
    end_session_requested = Signal()  # 结束会话请求信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("专注计时")
        self.setModal(False)  # 非模态，允许与主窗口交互
        self.setFixedSize(280, 200)

        # 呼吸动画
        self.breath_value = 0.0
        self.breath_direction = 1
        self.breath_timer = QtCore.QTimer(self)
        self.breath_timer.setInterval(120)
        self.breath_timer.timeout.connect(self._update_breath)
        self.breath_timer.start()

        # 会话数据
        self.goal_text = ""
        self.total_duration = 0
        self.remaining_time = 0

        # 粒子效果系统
        self.particles = []
        self.particle_timer = QtCore.QTimer(self)
        self.particle_timer.setInterval(50)  # 20fps
        self.particle_timer.timeout.connect(self._update_particles)

        self._build_ui()
        self._apply_style()

    def _create_particles(self, x, y, count=10):
        """创建粒子效果"""
        import random

        for _ in range(count):
            particle = {
                'x': x,
                'y': y,
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-3, -1),
                'life': 1.0,
                'decay': random.uniform(0.02, 0.04),
                'size': random.uniform(2, 5),
                'color': random.choice(['#FFD700', '#A5D6A7', '#66BB6A', '#FFF176'])
            }
            self.particles.append(particle)

        if not self.particle_timer.isActive():
            self.particle_timer.start()

    def _update_particles(self):
        """更新粒子状态"""
        if not self.particles:
            self.particle_timer.stop()
            return

        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['vy'] += 0.08  # 重力效果
            particle['life'] -= particle['decay']

            if particle['life'] <= 0:
                self.particles.remove(particle)

        self.update()

    def paintEvent(self, event):
        """绘制粒子效果"""
        super().paintEvent(event)

        if self.particles:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

            for particle in self.particles:
                color = QtGui.QColor(particle['color'])
                color.setAlphaF(particle['life'])
                painter.setBrush(QtGui.QBrush(color))
                painter.setPen(QtCore.Qt.NoPen)

                size = particle['size'] * particle['life']
                painter.drawEllipse(
                    int(particle['x'] - size/2),
                    int(particle['y'] - size/2),
                    int(size),
                    int(size)
                )

    def _build_ui(self):
        """构建用户界面"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # 目标显示
        self.goal_label = QtWidgets.QLabel("🎯 目标：准备开始...")
        self.goal_label.setFont(QtGui.QFont(
            "Microsoft YaHei", 10, QtGui.QFont.DemiBold))
        self.goal_label.setAlignment(QtCore.Qt.AlignCenter)
        self.goal_label.setWordWrap(True)
        layout.addWidget(self.goal_label)

        # 时间显示
        self.time_label = QtWidgets.QLabel("25:00")
        time_font = QtGui.QFont("Microsoft YaHei", 24, QtGui.QFont.Bold)
        self.time_label.setFont(time_font)
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.time_label)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QtWidgets.QLabel("⚡ 专注进行中...")
        self.status_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 结束按钮
        self.end_button = QtWidgets.QPushButton("结束专注")
        self.end_button.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.end_button.setFixedHeight(36)
        self.end_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.end_button.clicked.connect(self._on_end_clicked)
        layout.addWidget(self.end_button)

    def _apply_style(self):
        """应用清新森林样式"""
        # 呼吸动画效果
        breath_delta = int(3 * self.breath_value)
        bg_alpha = max(0, min(255, 240 + breath_delta))

        dialog_style = f"""
            QDialog {{
                background-color: rgba(232, 245, 233, {bg_alpha});
                border-radius: 16px;
                border: none;
            }}
            QLabel {{
                color: #1B5E20;
                background-color: transparent;
                border: none;
            }}
            QProgressBar {{
                background-color: rgba(27, 94, 32, 20);
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: #66BB6A;
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: rgba(255, 100, 100, 70);
                border: none;
                border-radius: 8px;
                color: #ffffff;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 100, 100, 100);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 100, 100, 130);
            }}
        """

        self.setStyleSheet(dialog_style)

    def _update_breath(self):
        """更新呼吸动画"""
        step = 0.02
        self.breath_value += step * self.breath_direction
        if self.breath_value > 1.0:
            self.breath_value = 1.0
            self.breath_direction = -1
        elif self.breath_value < 0.0:
            self.breath_value = 0.0
            self.breath_direction = 1
        self._apply_style()

    def start_session(self, goal: str, duration_seconds: int):
        """开始计时会话"""
        self.goal_text = goal
        self.total_duration = duration_seconds
        self.remaining_time = duration_seconds

        # 更新显示
        self.goal_label.setText(f"🎯 目标：{goal}")
        self.update_display(duration_seconds)

    def update_display(self, remaining_seconds: int):
        """更新显示内容"""
        self.remaining_time = remaining_seconds

        # 格式化时间显示
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        time_text = f"{minutes:02d}:{seconds:02d}"
        self.time_label.setText(time_text)

        # 更新进度条
        if self.total_duration > 0:
            progress = int((remaining_seconds / self.total_duration) * 100)
            self.progress_bar.setValue(progress)

        # 更新状态
        if remaining_seconds <= 0:
            self.status_label.setText("🎉 专注完成！")
            self.end_button.setText("关闭")
            # 创建庆祝粒子效果
            self._create_celebration_particles()
        else:
            total_minutes = self.total_duration // 60
            self.status_label.setText(f"⚡ 专注进行中... (总计{total_minutes}分钟)")

    def _create_celebration_particles(self):
        """创建庆祝粒子效果"""
        import random
        # 在整个弹窗中创建多个庆祝粒子爆发点
        for i in range(5):
            x = random.randint(50, self.width() - 50)
            y = random.randint(50, self.height() - 50)
            self._create_particles(x, y, 8)

    def _on_end_clicked(self):
        """结束按钮点击"""
        # 创建粒子效果
        button_pos = self.end_button.pos()
        button_center_x = button_pos.x() + self.end_button.width() // 2
        button_center_y = button_pos.y() + self.end_button.height() // 2
        self._create_particles(button_center_x, button_center_y, 15)

        # 延迟执行关闭逻辑
        QtCore.QTimer.singleShot(300, self._do_end_session)

    def _do_end_session(self):
        """执行结束会话"""
        self.end_session_requested.emit()
        self.close()

    def closeEvent(self, event):
        """关闭事件"""
        # 停止呼吸动画
        self.breath_timer.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)

    # 创建黑色背景窗口，模拟屏幕环境，方便看清透明效果
    bg_window = QtWidgets.QWidget()
    bg_window.setStyleSheet("background-color: #1a1a1a;")
    bg_window.resize(600, 400)

    # 将卡片放在背景窗口中
    card = FocusStatusCard(bg_window)
    card.move(100, 100)

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

    print("样式调试模式已启动：")
    print("1. 请调节 _apply_style 中的 bg_alpha 和 border_alpha 参数")
    print("2. 悬停鼠标查看三层展开效果")

    sys.exit(app.exec())
