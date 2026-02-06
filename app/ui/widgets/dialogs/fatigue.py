# -*- coding: utf-8 -*-
"""
[正在使用]
用于显示"工作疲劳"的详细提醒弹窗（包含休息建议、倒计时等复杂功能）。
被 main.py 直接调用（FatigueReminderDialog），用于每隔一段时间强制休息。
"""

import sys
import os
import time

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QColor
    from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QFrame, QStackedLayout
except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QFont, QColor
        from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QFrame, QStackedLayout


class FatigueReminderDialog(QDialog):
    """工作疲劳提醒对话框"""
    
    def __init__(self, severity='medium', duration=120, parent=None):
        super().__init__(parent)
        self.severity = severity
        self.duration = duration
        
        self.setWindowTitle("工作疲劳提醒")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 720)
        
        self.setup_ui()
        self._center_window()
        
        # 休息计时器
        self.rest_timer = QTimer(self)
        self.rest_timer.timeout.connect(self._on_timer_tick)
        self.remaining_time = 0
        
        # 拖拽支持：全窗口任意位置可拖动
        self._drag_active = False
        self._drag_offset = None
        
    def _center_window(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.x() + (geometry.width() - self.width()) // 2
            y = geometry.y() + (geometry.height() - self.height()) // 2
            self.move(x, y)
        
    def setup_ui(self):
        """构建UI"""
        # 主布局使用堆叠布局，方便切换页面
        self.stacked_layout = QStackedLayout()
        
        # 页面1：提醒页面
        self.reminder_page = QtWidgets.QWidget()
        self._setup_reminder_page(self.reminder_page)
        self.stacked_layout.addWidget(self.reminder_page)
        
        # 页面2：休息建议列表页面
        self.suggestion_page = QtWidgets.QWidget()
        self._setup_suggestion_page(self.suggestion_page)
        self.stacked_layout.addWidget(self.suggestion_page)
        
        # 页面3：休息计时页面
        self.timer_page = QtWidgets.QWidget()
        self._setup_timer_page(self.timer_page)
        self.stacked_layout.addWidget(self.timer_page)
        
        self.setLayout(self.stacked_layout)
        
    def _setup_reminder_page(self, parent_widget):
        """构建提醒页面"""
        main_layout = QVBoxLayout(parent_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 背景框架
        self.bg_frame = QFrame()
        try:
            from app.ui.widgets.report.theme import theme as MorandiTheme
        except ImportError:
            try:
                from app.ui.widgets.report.theme import theme as MorandiTheme
            except ImportError:
                from app.ui.widgets.report.theme import theme as MorandiTheme
        gradient_start = MorandiTheme.HEX_REMINDER_GRADIENT_START
        gradient_end = MorandiTheme.HEX_REMINDER_GRADIENT_END
        panel_fill = MorandiTheme.HEX_REMINDER_PANEL_FILL
        self.bg_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 {gradient_start},
                                            stop:1 {gradient_end});
                border-radius: 20px;
                border: none;
            }}
        """)
        
        bg_layout = QVBoxLayout()
        bg_layout.setContentsMargins(40, 20, 40, 40)  # 减少顶部边距 (40 -> 20)
        bg_layout.setSpacing(15)  # 减少整体控件间距 (25 -> 15)
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 24px;
                color: #999;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #e74c3c;
            }
        """)
        # 这里的关闭是完全退出
        close_btn.clicked.connect(self.reject)
        
        # 顶部区域 (关闭按钮)
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        
        # 将顶部布局插入到主背景布局的最开始，并且不添加额外的间距
        bg_layout.addLayout(top_layout)
        
        # 头部整体区域（图标+标题）
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet(f"""
            QFrame#headerFrame {{
                background-color: {panel_fill};
                border-radius: 20px;
                border: 1px solid rgba(0, 0, 0, 0.03);
            }}
            QFrame#headerFrame:hover {{
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }}
        """)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(10)
        
        # 图标 (居中)
        icon_label = QLabel("🍃")
        icon_label.setFont(QFont("Arial", 48))
        icon_label.setFixedSize(100, 100)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        # 标题 (居中)
        title = QLabel("嘿，学霸～")
        title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        title.setStyleSheet("color: #1B5E20; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        # 描述文本 (在方框外)
        severity_text = self._get_severity_text()
        severity_label = QLabel(severity_text)
        severity_label.setFont(QFont("Microsoft YaHei", 13))
        severity_label.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        severity_label.setAlignment(Qt.AlignCenter)
        
        # 使用负边距将整体向上拉
        bg_layout.addSpacing(-20)
        bg_layout.addWidget(header_frame)
        bg_layout.addWidget(severity_label)
        
        # 确保关闭按钮在最上层，防止被header_frame遮挡
        close_btn.raise_()
        
        # 统计信息区域
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(30)
        
        # 持续时长
        duration_widget = self._create_stat_widget(
            "⏱️",
            "连续工作",
            f"{self.duration}分钟",
            "#66BB6A"
        )
        stats_layout.addWidget(duration_widget)
        
        # 严重程度
        severity_widget = self._create_stat_widget(
            "⚡",
            "疲劳程度",
            self._get_severity_cn(),
            self._get_severity_color()
        )
        stats_layout.addWidget(severity_widget)
        
        bg_layout.addLayout(stats_layout)
        
        # 建议文本区域
        suggestion_frame = QFrame()
        suggestion_frame.setObjectName("suggestionFrame")
        suggestion_frame.setStyleSheet(f"""
            QFrame#suggestionFrame {{
                background-color: {panel_fill};
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.03);
            }}
            QFrame#suggestionFrame:hover {{
                background-color: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }}
        """)
        
        sugg_layout = QVBoxLayout(suggestion_frame)
        sugg_layout.setContentsMargins(20, 15, 20, 15)
        
        suggestion = QLabel(self._get_suggestion())
        suggestion.setFont(QFont("Microsoft YaHei", 12))
        suggestion.setStyleSheet("color: #34495e; line-height: 1.6; background: transparent; border: none;")
        suggestion.setWordWrap(True)
        suggestion.setAlignment(Qt.AlignCenter)
        
        sugg_layout.addWidget(suggestion)
        bg_layout.addWidget(suggestion_frame)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        rest_btn = QPushButton("休息会儿 😌")
        rest_btn.setFixedHeight(45)
        rest_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        rest_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        # 切换到建议列表页面
        rest_btn.clicked.connect(self._on_rest_clicked)
        
        continue_btn = QPushButton("这题马上做完 💪")
        continue_btn.setFixedHeight(45)
        continue_btn.setFont(QFont("Microsoft YaHei", 12))
        continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #5d6d7b;
            }
        """)
        continue_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(rest_btn)
        btn_layout.addWidget(continue_btn)
        
        bg_layout.addLayout(btn_layout)
        
        self.bg_frame.setLayout(bg_layout)
        main_layout.addWidget(self.bg_frame)

    def _setup_suggestion_page(self, parent_widget):
        """构建休息建议列表页面"""
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 背景容器
        bg_frame = QFrame()
        bg_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: none;
            }
        """)
        
        content_layout = QVBoxLayout(bg_frame)
        content_layout.setContentsMargins(30, 40, 30, 40)
        content_layout.setSpacing(20)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("←")
        back_btn.setFixedSize(40, 40)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 24px;
                color: #7f8c8d;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #2c3e50;
                background-color: rgba(0,0,0,0.05);
                border-radius: 20px;
            }
        """)
        back_btn.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(0))
        
        title = QLabel("选择一种休息方式")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setStyleSheet("color: #1B5E20;")
        
        header_layout.addWidget(back_btn)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        content_layout.addLayout(header_layout)
        
        # 建议列表
        suggestions = [
            ("🚶", "户外散步", "10min", "#e8f5e9", "#2e7d32"),
            ("💧", "喝水眺望", "5min", "#e3f2fd", "#1565c0"),
            ("📚", "看书休息", "10min", "#fff3e0", "#ef6c00"),
            ("🧘", "原地走走", "5min", "#f3e5f5", "#7b1fa2"),
            ("🧘‍♀️", "冥想放松", "5min", "#e0f2f1", "#00695c"),
            ("🎵", "听听音乐", "10min", "#fce4ec", "#c2185b"),
            ("🤸", "大课间", "15min", "#fffde7", "#fbc02d")
        ]
        
        # 滚动区域
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #95a5a6;
            }
        """)
        
        scroll_content = QtWidgets.QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        for icon, name, time_str, bg_color, text_color in suggestions:
            btn = QPushButton()
            btn.setFixedHeight(70)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    border: none;
                    border-radius: 12px;
                    text-align: left;
                    padding: 0 20px;
                }}
                QPushButton:hover {{
                    background-color: {bg_color}EE;  /* 稍微加深 */
                    border: 2px solid {text_color}40;
                }}
            """)
            
            # 使用布局在按钮内部放置内容
            btn_layout = QHBoxLayout(btn)
            btn_layout.setContentsMargins(10, 0, 10, 0)
            
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(QFont("Segoe UI Emoji", 24))
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            name_lbl = QLabel(name)
            name_lbl.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
            name_lbl.setStyleSheet(f"color: {text_color}; border: none; background: transparent;")
            
            time_lbl = QLabel(time_str)
            time_lbl.setFont(QFont("Arial", 10))
            time_lbl.setStyleSheet(f"color: {text_color}AA; border: none; background: transparent;") # 半透明
            
            text_layout.addStretch()
            text_layout.addWidget(name_lbl)
            text_layout.addWidget(time_lbl)
            text_layout.addStretch()
            
            arrow_lbl = QLabel("➜")
            arrow_lbl.setFont(QFont("Arial", 16))
            arrow_lbl.setStyleSheet(f"color: {text_color}80; border: none; background: transparent;")
            
            btn_layout.addWidget(icon_lbl)
            btn_layout.addSpacing(15)
            btn_layout.addLayout(text_layout)
            btn_layout.addStretch()
            btn_layout.addWidget(arrow_lbl)
            
            # 点击建议进入计时页面
            # btn.clicked.connect(self.accept)
            btn.clicked.connect(lambda checked, n=name, t=time_str: self._start_rest_timer(n, t))
            
            scroll_layout.addWidget(btn)
            
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        
        content_layout.addWidget(scroll)
        layout.addWidget(bg_frame)
        
    def _setup_timer_page(self, parent_widget):
        """构建休息计时页面"""
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 背景容器
        bg_frame = QFrame()
        bg_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                border: none;
            }
        """)
        
        content_layout = QVBoxLayout(bg_frame)
        content_layout.setContentsMargins(40, 60, 40, 60)
        content_layout.setSpacing(30)

        # 添加最小化按钮（仅在倒计时进行时显示）
        top_toolbar = QHBoxLayout()
        top_toolbar.addStretch()
        self.minimize_btn = QPushButton("最小化")
        # 保留高度，宽度根据文本自适应
        self.minimize_btn.setMinimumHeight(40)
        self.minimize_btn.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 20px;
                color: #7f8c8d;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #2c3e50;
                background-color: rgba(0,0,0,0.03);
                border-radius: 20px;
            }
        """)
        self.minimize_btn.clicked.connect(self._on_minimize_clicked)
        self.minimize_btn.setContentsMargins(8, 0, 8, 0)
        self.minimize_btn.adjustSize()
        # 初始隐藏，只有在计时开始时显示
        try:
            self.minimize_btn.hide()
        except Exception:
            pass
        top_toolbar.addWidget(self.minimize_btn)
        content_layout.addLayout(top_toolbar)
        
        # 活动标题
        self.timer_activity_label = QLabel("正在休息")
        self.timer_activity_label.setFont(QFont("Microsoft YaHei", 16))
        self.timer_activity_label.setStyleSheet("color: #7f8c8d;")
        self.timer_activity_label.setAlignment(Qt.AlignCenter)
        
        # 倒计时显示
        self.timer_display_label = QLabel("00:00")
        self.timer_display_label.setFont(QFont("Arial", 64, QFont.Bold))
        self.timer_display_label.setStyleSheet("color: #1B5E20;")
        self.timer_display_label.setAlignment(Qt.AlignCenter)
        
        # 完成消息 (初始隐藏)
        self.timer_message_label = QLabel("🍃疲劳度下降为0%，我们继续加油吧！")
        self.timer_message_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.timer_message_label.setStyleSheet("color: #27ae60;")
        self.timer_message_label.setAlignment(Qt.AlignCenter)
        self.timer_message_label.setWordWrap(True)
        self.timer_message_label.hide()
        
        # 按钮容器
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.timer_skip_btn = QPushButton("结束休息")
        self.timer_skip_btn.setFixedSize(140, 45)
        self.timer_skip_btn.setFont(QFont("Microsoft YaHei", 12))
        self.timer_skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f2f6;
                color: #7f8c8d;
                border: none;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #e4e7eb;
                color: #2c3e50;
            }
        """)
        # 点击结束休息，直接触发完成逻辑
        self.timer_skip_btn.clicked.connect(self._on_rest_finished)
        
        btn_layout.addWidget(self.timer_skip_btn)
        # 完成后用户确认按钮（初始隐藏）
        self.timer_ack_btn = QPushButton("我知道了")
        self.timer_ack_btn.setFixedSize(140, 45)
        self.timer_ack_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.timer_ack_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.timer_ack_btn.clicked.connect(self.accept)
        self.timer_ack_btn.hide()
        btn_layout.addWidget(self.timer_ack_btn)
        btn_layout.addStretch()
        
        content_layout.addStretch()
        content_layout.addWidget(self.timer_activity_label)
        content_layout.addWidget(self.timer_display_label)
        content_layout.addWidget(self.timer_message_label)
        content_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        layout.addWidget(bg_frame)

    def _start_rest_timer(self, name, time_str):
        """开始休息计时"""
        # 解析时间 (例如 "10min" -> 600)
        minutes = int(time_str.replace("min", ""))
        # 为了演示效果，这里可以将时间缩短，比如 1min -> 5秒，或者真实计时
        # 考虑到用户体验，如果是演示，可以快一点
        # 这里使用真实时间，但如果时间太长，用户可以点结束
        self.remaining_time = minutes * 60
        
        # 更新 UI
        self.timer_activity_label.setText(f"正在进行：{name}")
        self._update_timer_display()
        self.timer_message_label.hide()
        self.timer_display_label.show()
        self.timer_skip_btn.setText("结束休息")
        self.timer_skip_btn.setEnabled(True)
        
        # 切换页面
        self.stacked_layout.setCurrentIndex(2)
        
        # 启动计时器
        # 显示最小化按钮（倒计时进行时）
        try:
            self.minimize_btn.show()
        except Exception:
            pass
        self.rest_timer.start(1000)

    def _on_timer_tick(self):
        """计时器滴答"""
        self.remaining_time -= 1
        self._update_timer_display()
        
        if self.remaining_time <= 0:
            self.rest_timer.stop()
            self._on_rest_finished()

    def _update_timer_display(self):
        """更新倒计时显示"""
        mins = self.remaining_time // 60
        secs = self.remaining_time % 60
        self.timer_display_label.setText(f"{mins:02d}:{secs:02d}")

    def _send_reset_signal(self):
        """发送重置信号给后端"""
        try:
            with open("reset_focus.signal", "w") as f:
                f.write("reset")
            print("[FatigueDialog] Sent reset signal to backend.")
        except Exception as e:
            print(f"[FatigueDialog] Failed to send reset signal: {e}")

    def accept(self):
        """重写 accept 方法，在休息完成后发送重置信号"""
        self._send_reset_signal()
        super().accept()

    def _on_rest_clicked(self):
        """点击休息按钮：发送重置信号并切换页面"""
        self._send_reset_signal()
        self.stacked_layout.setCurrentIndex(1)

    def _on_rest_finished(self):
        """休息完成"""
        self.rest_timer.stop()
        # 如果窗口被最小化或隐藏，先恢复并置顶
        try:
            if self.isMinimized() or not self.isVisible():
                try:
                    self.showNormal()
                except Exception:
                    pass
                try:
                    self.show()
                    self.raise_()
                    self.activateWindow()
                except Exception:
                    pass

        except Exception:
            # 保守回退：忽略任何检查错误
            pass

        # 更新 UI 显示完成状态
        self.timer_display_label.hide()
        self.timer_message_label.show()
        self.timer_activity_label.setText("休息完成")
        # 隐藏结束按钮，显示确认按钮，由用户点击关闭
        try:
            self.timer_skip_btn.hide()
        except Exception:
            pass
        # 隐藏最小化按钮（计时已结束）
        try:
            self.minimize_btn.hide()
        except Exception:
            pass
        try:
            self.timer_ack_btn.show()
            self.timer_ack_btn.setFocus()
        except Exception:
            # 如果确认按钮不存在，则回退为不自动关闭（保持在完成页）
            pass

    def _on_minimize_clicked(self):
        """最小化窗口（保持计时器运行）。"""
        try:
            self.showMinimized()
        except Exception:
            # 作为回退，隐藏窗口但保持计时器运行
            self.hide()

    def mousePressEvent(self, event):
        """鼠标按下：持续跟踪位置用于拖拽。"""
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动：若拖拽活跃，移动窗口。"""
        if self._drag_active and self._drag_offset is not None:
            self.move(event.globalPos() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：结束拖拽。"""
        if event.button() == Qt.LeftButton:
            self._drag_active = False
        super().mouseReleaseEvent(event)

    def _create_stat_widget(self, icon: str, label: str, value: str, color: str):
        """创建统计小部件"""
        widget = QtWidgets.QWidget()
        widget.setObjectName("statWidget")
        widget.setStyleSheet("""
            QWidget#statWidget {
                background-color: rgba(248, 249, 250, 200);
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.03);
            }
            QWidget#statWidget:hover {
                background-color: rgba(240, 242, 245, 220);
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 15)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 28))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setMinimumHeight(50)
        icon_label.setStyleSheet("background: transparent; border: none;")
        
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Microsoft YaHei", 10))
        label_widget.setStyleSheet("color: #7f8c8d; background: transparent; border: none;")
        label_widget.setAlignment(Qt.AlignCenter)
        
        value_widget = QLabel(value)
        value_widget.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        value_widget.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        value_widget.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        
        widget.setLayout(layout)
        return widget
    
    def _get_severity_text(self) -> str:
        """获取严重程度文本"""
        return f"你已经专注了{self.duration}分钟，大脑需要充会儿电啦"
    
    def _get_severity_cn(self) -> str:
        """获取严重程度中文"""
        return {'low': '低', 'medium': '中', 'high': '高'}.get(self.severity, '未知')
    
    def _get_severity_color(self) -> str:
        """获取严重程度颜色"""
        colors = {
            'low': '#66BB6A',
            'medium': '#f39c12',
            'high': '#e74c3c'
        }
        return colors.get(self.severity, '#95a5a6')
    
    def _calculate_fatigue_score(self) -> int:
        """计算疲劳指数"""
        if self.severity == 'low':
            return 30
        elif self.severity == 'medium':
            return 60
        else:
            return 90
    
    def _get_suggestion(self) -> str:
        """获取建议"""
        return "休息5~10min,产能将提升45%！"
