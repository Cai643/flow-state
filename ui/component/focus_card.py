try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal


class FocusStatusCard(QtWidgets.QWidget):
    """
    悬浮球联动的三层悬停专注卡片
    第1层：核心状态
    第2层：快捷操作
    第3层：高级控制
    """
    start_pomodoro_requested = Signal()
    pause_monitor_requested = Signal()
    enter_deep_mode_requested = Signal()
    set_goal_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)

        # 当前悬停层级：1/2/3
        self.hover_level = 1
        self.hovering = False
        self.locked_expanded = False # 点击后锁定展开状态

        # 拉回注意力次数（从娱乐 -> 工作 的切换次数）
        self.pull_back_count = 0
        self.last_status = None

        # 构建 UI
        self._build_ui()

        # 分层定时器：0.5s 出现第2层；1s 出现第3层
        self.level2_timer = QtCore.QTimer(self)
        self.level2_timer.setSingleShot(True)
        self.level2_timer.timeout.connect(self._activate_level2)

        self.level3_timer = QtCore.QTimer(self)
        self.level3_timer.setSingleShot(True)
        self.level3_timer.timeout.connect(self._activate_level3)

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
        # 第1层（紧凑）：约 120-130px
        # 第2层（展开快捷）：约 160-170px
        # 第3层（完全展开）：约 200-210px
        
        base_h = 150 # 第1层基础高度 (标题30 + 进度6 + 状态30 + 摘要30 + 间距 + 边距)
        
        if self.hover_level == 1:
            h = base_h
        elif self.hover_level == 2:
            h = base_h + 70 # 快捷操作高度 (标题 + 按钮24 + 间距)
        else:
            h = base_h + 70 + 70 # 高级操作高度
            
        return QtCore.QSize(250, h)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # 减小边距
        layout.setSpacing(6) # 减小间距

        # 通用内部条目样式 (Label带有背景)
        self.item_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(168, 216, 234, 50);
                border-radius: 12px;
                padding: 2px 10px;
                color: #e0f0f8;
            }
        """

        # 第1层：核心状态
        self.title_label = QtWidgets.QLabel("🎯 今日专注  0.0h / 8h")
        title_font = QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.DemiBold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(self.item_style)
        self.title_label.setFixedHeight(30) # 减小高度

        # 进度条：今日专注完成度
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6) # 减小高度
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 0px;
                background-color: rgba(255, 255, 255, 25);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #64b5f6; /* 更亮的蓝色 */
                border-radius: 3px;
            }
        """)

        self.status_label = QtWidgets.QLabel("⚡ 专注中  已连续0分钟")
        self.status_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet(self.item_style)
        self.status_label.setFixedHeight(30) # 减小高度

        self.summary_label = QtWidgets.QLabel("💪 拉回注意力 0次  ↑效率+0%")
        self.summary_label.setFont(QtGui.QFont("Microsoft YaHei", 9))
        self.summary_label.setStyleSheet(self.item_style)
        self.summary_label.setFixedHeight(30) # 减小高度

        layout.addWidget(self.title_label)
        layout.addWidget(self.progress)
        layout.addSpacing(2)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)

        # 容器通用样式
        container_style = """
            QWidget {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(168, 216, 234, 50);
                border-radius: 12px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #a8d8ea;
            }
        """

        # 第2层：快捷操作
        self.quick_container = QtWidgets.QWidget(self)
        self.quick_container.setStyleSheet(container_style)
        quick_layout = QtWidgets.QVBoxLayout(self.quick_container)
        quick_layout.setContentsMargins(10, 8, 10, 8)
        quick_layout.setSpacing(6)

        quick_title = QtWidgets.QLabel("🎬 快速操作")
        quick_title.setFont(QtGui.QFont("Microsoft YaHei", 9))

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_pomodoro = QtWidgets.QPushButton("开始番茄钟")
        self.btn_pause = QtWidgets.QPushButton("暂停监测")
        
        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border-radius: 12px;
                border: 0px;
                color: #a8d8ea;
                padding: 0 10px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 40);
            }
        """
        for btn in (self.btn_pomodoro, self.btn_pause):
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet(btn_style)

        btn_row.addWidget(self.btn_pomodoro)
        btn_row.addWidget(self.btn_pause)

        quick_layout.addWidget(quick_title)
        quick_layout.addLayout(btn_row)

        layout.addWidget(self.quick_container)

        # 第3层：高级控制
        self.advanced_container = QtWidgets.QWidget(self)
        self.advanced_container.setStyleSheet(container_style)
        adv_layout = QtWidgets.QVBoxLayout(self.advanced_container)
        adv_layout.setContentsMargins(10, 8, 10, 8)
        adv_layout.setSpacing(6)

        adv_title = QtWidgets.QLabel("⚙️ 高级")
        adv_title.setFont(QtGui.QFont("Microsoft YaHei", 9))

        adv_btn_row = QtWidgets.QHBoxLayout()
        adv_btn_row.setSpacing(8)

        self.btn_deep = QtWidgets.QPushButton("进入深度模式")
        self.btn_goal = QtWidgets.QPushButton("设目标")
        for btn in (self.btn_deep, self.btn_goal):
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setFixedHeight(24)
            btn.setStyleSheet(btn_style)

        adv_btn_row.addWidget(self.btn_deep)
        adv_btn_row.addWidget(self.btn_goal)

        adv_layout.addWidget(adv_title)
        adv_layout.addLayout(adv_btn_row)

        layout.addWidget(self.advanced_container)

        # 按钮信号向外转发
        self.btn_pomodoro.clicked.connect(self.start_pomodoro_requested.emit)
        self.btn_pause.clicked.connect(self.pause_monitor_requested.emit)
        self.btn_deep.clicked.connect(self.enter_deep_mode_requested.emit)
        self.btn_goal.clicked.connect(self.set_goal_requested.emit)

        # 初始只展示第1层
        self.quick_container.setVisible(False)
        self.advanced_container.setVisible(False)

    # --- 交互逻辑说明 ---
    # 1. 悬停展开逻辑：
    #    - 鼠标进入 (enterEvent)：开始计时。0.5秒后展开第2层，1秒后展开第3层。
    #    - 鼠标离开 (leaveEvent)：立即恢复到第1层（紧凑视图），除非处于“锁定展开”模式。
    #    - 定时器 (level2_timer, level3_timer)：控制自动展开的节奏。
    
    def enterEvent(self, event):
        self.hovering = True
        
        # 如果已经锁定展开，直接显示最大层级
        if self.locked_expanded:
            self.hover_level = 3
            self._update_visibility_by_level()
        else:
            # 初始状态：只显示第1层
            self.hover_level = 1
            self._update_visibility_by_level()
            
            # 启动定时器，实现“悬停久一点才慢慢展开”
            # 修改这里的时间可以调整展开速度
            self.level2_timer.start(500)  # 500ms 后展开快捷操作
            self.level3_timer.start(1000) # 1000ms 后展开高级选项
            
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovering = False
        self.level2_timer.stop()
        self.level3_timer.stop()
        
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
                self.hover_level = 3
                # 停止自动展开定时器，因为已经强制展开了
                self.level2_timer.stop()
                self.level3_timer.stop()
            else:
                # 解锁后，根据当前鼠标是否悬停决定层级
                # 如果鼠标还在上面，保持展开；如果不在，收缩
                self.hover_level = 3 if self.hovering else 1
            
            self._update_visibility_by_level()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _activate_level2(self):
        if self.hovering and self.hover_level < 2 and not self.locked_expanded:
            self.hover_level = 2
            self._update_visibility_by_level()

    def _activate_level3(self):
        if self.hovering and self.hover_level < 3 and not self.locked_expanded:
            self.hover_level = 3
            self._update_visibility_by_level()

    def _update_visibility_by_level(self):
        # 根据悬停层级控制容器显示
        is_level2 = self.hover_level >= 2
        is_level3 = self.hover_level >= 3
        
        # 隐藏/显示容器
        # 注意：设置为不可见后，布局会自动调整大小（收缩）
        self.quick_container.setVisible(is_level2)
        self.advanced_container.setVisible(is_level3)
        
        # 强制更新几何形状，确保父窗口（如果有）能感知到大小变化
        self.adjustSize()
        if self.parentWidget():
            self.parentWidget().adjustSize()
            
        self._apply_style()

    def _apply_style(self):
        # --- 样式参数调节区 ---
        # 说明：alpha 值范围 0-255，值越大越不透明
        # 莫兰迪蓝基色: #a8d8ea (RGB: 168, 216, 234)
        
        # 使用深色半透明背景 (接近黑色/深灰)
        # 背景色：rgba(40, 45, 50, alpha)
        # 边框色：rgba(168, 216, 234, border_alpha)

        if self.hover_level == 1:
            bg_alpha = 230    # 之前是180，提高更实
            border_alpha = 140 # 之前是80
        elif self.hover_level == 2:
            bg_alpha = 245    # 之前是200
            border_alpha = 180 # 之前是120
        else:
            bg_alpha = 255    # 之前是220
            border_alpha = 220 # 之前是160
        
        # 叠加轻微呼吸动画（0.95-1.0）
        breath_delta = int(3 * self.breath_value)
        # 这里的bg_alpha控制的是深色底的不透明度
        current_bg_alpha = max(0, min(255, bg_alpha + breath_delta))

        style = f"""
            QWidget {{
                background-color: rgba(40, 44, 52, {current_bg_alpha});
                border-radius: 16px;
                border: 1px solid rgba(168, 216, 234, {border_alpha});
                color: #e0f0f8;
            }}
            /* 进度条样式覆盖 */
            QProgressBar {{
                background-color: rgba(255, 255, 255, 20);
                border: none;
            }}
        """
        self.setStyleSheet(style)

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
        target_hours = 8.0
        percent = int(min(100, (focus_hours / target_hours) * 100))

        self.title_label.setText(f"🎯 今日专注  {focus_hours:.1f}h / {target_hours:.0f}h")
        self.progress.setValue(percent)

        minutes = int(duration / 60.0)
        if status == "working":
            self.status_label.setText(f"⚡ 专注中  已连续{minutes}分钟")
        elif status == "entertainment":
            self.status_label.setText(f"🎮 娱乐中  已连续{minutes}分钟")
        elif status == "idle":
            self.status_label.setText(f"⏸ 暂离  已连续{minutes}分钟")
        else:
            self.status_label.setText(f"📟 状态识别中  已持续{minutes}分钟")

        # 统计从“娱乐”切回“工作”的次数，近似理解为“拉回注意力”
        if self.last_status == "entertainment" and status == "working":
            self.pull_back_count += 1
        self.last_status = status

        efficiency_gain = min(50, self.pull_back_count * 5)
        self.summary_label.setText(
            f"💪 拉回注意力 {self.pull_back_count}次  ↑效率+{efficiency_gain}%"
        )


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
        status = random.choice(["working", "working", "working", "entertainment", "idle"])
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

