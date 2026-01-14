
try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui

import random
from datetime import datetime, date
from app.ui.widgets.report.theme import theme
from app.data import ActivityHistoryManager

class SimpleDailyReport(QtWidgets.QWidget):
    """
    全景式+强反馈 长方形时间轴日报
    核心理念：Time Blocks (积木堆叠)
    """
    clicked = QtCore.Signal()  # 点击信号，用于关闭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # 数据管理器
        self.history_manager = ActivityHistoryManager()
        
        # 尺寸设置 (横向正方形)
        self.setFixedSize(800, 750)
        
        # 加载数据
        self._load_data()
        
        self._build_ui()
        self._center_on_screen()
        
        # 入场动画
        self.setWindowOpacity(0.0)
        self.anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(400)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def _load_data(self):
        """加载数据并生成时间轴块"""
        # 1. 获取统计摘要 (Header)
        summary = self.history_manager.get_daily_summary() or {}
        total_focus_seconds = summary.get('total_focus_time', 0)
        self.total_focus_minutes = int(total_focus_seconds / 60)
        
        # 生成超越百分比 (Mock logic based on focus time)
        self.beat_percentage = min(99, int(self.total_focus_minutes / 4.8)) # 假设8小时是100%
        
        hours = self.total_focus_minutes // 60
        minutes = self.total_focus_minutes % 60
        if hours > 0:
            self.duration_text = f"{hours}h {minutes}m"
        else:
            self.duration_text = f"{minutes}m"
            
        # 2. 获取详细日志并合并 (Timeline)
        raw_logs = self.history_manager.get_daily_logs()
        self.time_blocks = self._process_logs_to_blocks(raw_logs)

    def _process_logs_to_blocks(self, logs):
        """将原始日志合并为时间块 (Chunking)"""
        # 强制使用Mock数据
        return self._get_mock_blocks()

    def _get_mock_blocks(self):
        return [
            {
                "time": "06:37 - 07:26",
                "duration_text": "50m",
                "type": "A",
                "status_raw": "focus",
                "title": "深度攻坚",
                "desc": "AI: 这段代码写得太丝滑了！",
                "badge": "S级",
                "duration_mins": 50
            },
            {
                "time": "07:26 - 07:40",
                "duration_text": "14m",
                "type": "B",
                "status_raw": "entertainment",
                "title": "充电",
                "desc": "",
                "badge": "☕",
                "duration_mins": 14
            },
            {
                "time": "07:40 - 07:45",
                "duration_text": "5m",
                "type": "C",
                "status_raw": "other",
                "title": "",
                "desc": "",
                "badge": None,
                "duration_mins": 5
            },
            {
                "time": "07:45 - 08:30",
                "duration_text": "45m",
                "type": "A",
                "status_raw": "focus",
                "title": "知识吸收",
                "desc": "能量积累中...",
                "badge": "专注",
                "duration_mins": 45
            },
            {
                "time": "08:30 - 10:30",
                "duration_text": "120m",
                "type": "A",
                "status_raw": "focus",
                "title": "深度心流",
                "desc": "太强了！连续战斗2小时！",
                "badge": "S级",
                "duration_mins": 120
            }
        ]
        
    def _build_scroll_timeline(self, parent_layout):
        # 创建横向滚动区域
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        # 滚动条样式
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:horizontal {
                border: none;
                background: #F0F4E8;
                height: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #C2E3B8;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        content = QtWidgets.QWidget()
        content.setStyleSheet("background: transparent;")
        
        # 横向布局
        layout = QtWidgets.QHBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5) # 积木间距
        layout.setAlignment(QtCore.Qt.AlignLeft)
        
        # Add Blocks
        for block in self.time_blocks:
            w = self._create_block_widget(block)
            layout.addWidget(w)
            
        layout.addStretch()
        scroll.setWidget(content)
        parent_layout.addWidget(scroll)

    def _create_block_widget(self, data):
        """根据类型和时长创建横向拉伸的积木"""
        w = QtWidgets.QWidget()
        
        # 计算宽度: 1分钟 = 3px (基础比例)
        # 最小宽度 30px
        width = max(30, data.get('duration_mins', 10) * 3)
        w.setFixedWidth(width)
        
        # 设置固定高度，形成横向长条
        w.setFixedHeight(300) 
        
        if data['type'] == 'A':
            # A类：专注长块 (绿色渐变)
            w.setStyleSheet(f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E8F5E9, stop:1 #C8E6C9);
                    border: 1px solid #4CAF50;
                    border-radius: 8px;
                }}
                QWidget:hover {{
                    background: #A5D6A7;
                    border: 2px solid #2E7D32;
                }}
            """)
            
            # 内部布局
            v_layout = QtWidgets.QVBoxLayout(w)
            v_layout.setContentsMargins(5, 10, 5, 10)
            
            # Icon
            icon = QtWidgets.QLabel("🌳")
            icon.setAlignment(QtCore.Qt.AlignCenter)
            icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
            v_layout.addWidget(icon)
            
            # Title (如果够宽)
            if width > 60:
                title = QtWidgets.QLabel(f"{data['title']}\n({data['duration_text']})")
                title.setAlignment(QtCore.Qt.AlignCenter)
                title.setWordWrap(True)
                title.setStyleSheet("color: #1B5E20; font-weight: bold; font-size: 12px; border: none; background: transparent;")
                v_layout.addWidget(title)
            
            # AI Comment Bubble (Tooltip style inside)
            if width > 100:
                comment = QtWidgets.QLabel(data['desc'])
                comment.setWordWrap(True)
                comment.setAlignment(QtCore.Qt.AlignCenter)
                comment.setStyleSheet("color: #558B2F; font-size: 10px; font-style: italic; border: none; background: transparent; margin-top: 5px;")
                v_layout.addWidget(comment)
                
            v_layout.addStretch()
            
            # Tooltip for hover
            w.setToolTip(f"{data['title']} ({data['duration_text']})\n{data['desc']}")

        elif data['type'] == 'B':
            # B类：休息短块 (米黄色)
            w.setStyleSheet("""
                QWidget {
                    background-color: #FFF9C4;
                    border: 1px solid #FFF59D;
                    border-radius: 8px;
                }
                QWidget:hover {
                    background-color: #FFF59D;
                }
            """)
            
            v_layout = QtWidgets.QVBoxLayout(w)
            v_layout.setContentsMargins(2, 5, 2, 5)
            v_layout.setAlignment(QtCore.Qt.AlignCenter)
            
            icon = QtWidgets.QLabel("☕")
            icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
            v_layout.addWidget(icon)
            
            if width > 40:
                lbl = QtWidgets.QLabel("充电")
                lbl.setStyleSheet("color: #795548; font-size: 10px; border: none; background: transparent;")
                v_layout.addWidget(lbl)
                
            w.setToolTip(f"休息充电 ({data['duration_text']})")

        else:
            # C类：碎片 (灰色)
            w.setStyleSheet("""
                QWidget {
                    background-color: #F5F5F5;
                    border: 1px dashed #BDBDBD;
                    border-radius: 4px;
                }
            """)
            w.setToolTip(f"碎片时间 ({data['duration_text']})")
            
        return w

    def _build_ui(self):
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 背景容器
        container = QtWidgets.QWidget()
        container.setObjectName("MainContainer")
        # Cream/Honeydew Background
        container.setStyleSheet("""
            QWidget#MainContainer {
                background-color: #F7F9F2; /* Lighter Honeydew */
                border-radius: 20px;
                border: 2px solid #50795D;
            }
        """)
        main_layout.addWidget(container)
        
        content_layout = QtWidgets.QVBoxLayout(container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # --- Header Section ---
        self._build_header(content_layout)
        
        # --- Scrollable Timeline ---
        self._build_scroll_timeline(content_layout)
        
        # --- Footer Section ---
        self._build_footer(content_layout)

    def _build_header(self, parent_layout):
        header = QtWidgets.QWidget()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            background-color: #50795D;
            border-top-left-radius: 18px;
            border-top-right-radius: 18px;
        """)
        
        layout = QtWidgets.QVBoxLayout(header)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Top Row: Back + Date
        top_row = QtWidgets.QHBoxLayout()
        
        back_btn = QtWidgets.QPushButton("< 返回")
        back_btn.setCursor(QtCore.Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            color: #FFFFFF; font-weight: bold; border: none; font-size: 14px;
        """)
        back_btn.clicked.connect(self.close)
        
        date_label = QtWidgets.QLabel(date.today().strftime("%Y.%m.%d %A"))
        date_label.setStyleSheet("color: #C2E3B8; font-size: 14px;")
        
        top_row.addWidget(back_btn)
        top_row.addStretch()
        top_row.addWidget(date_label)
        
        layout.addLayout(top_row)
        
        # Stats Row
        stats_row = QtWidgets.QHBoxLayout()
        stats_row.setSpacing(20)
        
        # 使用 QFrame 来包含图标和文字
        s1_frame = QtWidgets.QFrame()
        s1_layout = QtWidgets.QHBoxLayout(s1_frame)
        s1_layout.setContentsMargins(0, 0, 0, 0)
        s1_layout.setSpacing(5)
        s1_icon = QtWidgets.QLabel("🌳")
        s1_icon.setStyleSheet("font-size: 16px;")
        s1_text = QtWidgets.QLabel(f"今日专注能量: {self.duration_text}")
        s1_text.setStyleSheet("color: #FFD700; font-weight: bold; font-size: 18px;") # 金色大字
        s1_layout.addWidget(s1_icon)
        s1_layout.addWidget(s1_text)
        
        s2 = QtWidgets.QLabel(f"⚡ 击败 {self.beat_percentage}% 用户")
        s2.setStyleSheet("color: #FFFFFF; font-size: 14px;")
        
        stats_row.addWidget(s1_frame)
        stats_row.addStretch()
        stats_row.addWidget(s2)
        
        layout.addLayout(stats_row)
        
        parent_layout.addWidget(header)

    def _build_footer(self, parent_layout):
        footer = QtWidgets.QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background-color: #FFFFFF; border-bottom-left-radius: 18px; border-bottom-right-radius: 18px;")
        
        layout = QtWidgets.QHBoxLayout(footer)
        layout.setContentsMargins(20, 10, 20, 10)
        
        btn = QtWidgets.QPushButton("分享今日成就")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #50795D;
                color: white;
                font-weight: bold;
                border-radius: 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        
        layout.addWidget(btn)
        parent_layout.addWidget(footer)

    def _center_on_screen(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = SimpleDailyReport()
    w.show()
    sys.exit(app.exec())
