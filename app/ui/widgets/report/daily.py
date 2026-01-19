
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
        # 修改：优先从 StatsDAO 获取实时数据 (daily_stats 表)
        try:
            from app.data.dao.activity_dao import StatsDAO
            summary = StatsDAO.get_daily_summary(date.today()) or {}
            # 兼容字段名
            f_time = summary.get('total_focus_time') or summary.get('focus_time') or 0
            w_time = summary.get('total_work_time') or summary.get('work_time') or 0
            total_focus_seconds = f_time + w_time
        except:
            # Fallback
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
        # 从 WindowSessionDAO 获取真实数据
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            from datetime import datetime
            
            sessions = WindowSessionDAO.get_today_sessions()
            
            blocks = []
            if not sessions:
                return blocks
                
            current_block = None
            
            for s in sessions:
                # 状态归类
                if s['status'] in ['work', 'focus']:
                    s_type = 'A'
                    s_title = "工作学习"
                elif s['status'] == 'entertainment':
                    s_type = 'B'
                    s_title = "充电"
                else:
                    s_type = 'C'
                    s_title = "碎片"
                
                # 检查是否可以合并到上一块
                if current_block and current_block['type'] == s_type:
                    # 合并
                    current_block['duration_sec'] += s['duration']
                    current_block['end_time_raw'] = s['end_time']
                    current_block['sub_items'].append(s)
                else:
                    # 结算上一块
                    if current_block:
                        self._finalize_block(current_block)
                        blocks.append(current_block)
                    
                    # 开启新块
                    current_block = {
                        'type': s_type,
                        'title': s_title,
                        'start_time_raw': s['start_time'],
                        'end_time_raw': s['end_time'],
                        'duration_sec': s['duration'],
                        'sub_items': [s],
                        'badge': None # 后续计算
                    }
            
            # 结算最后一块
            if current_block:
                self._finalize_block(current_block)
                blocks.append(current_block)
                
            return blocks
            
        except Exception as e:
            print(f"Error loading real sessions: {e}")
            return self._get_mock_blocks() # Fallback

    def _finalize_block(self, block):
        """计算 Block 的最终显示属性"""
        from datetime import datetime
        
        # 1. 时长文本
        duration_mins = max(1, int(block['duration_sec'] / 60))
        if duration_mins < 60:
            block['duration_text'] = f"{duration_mins}m"
        else:
            h = duration_mins // 60
            m = duration_mins % 60
            block['duration_text'] = f"{h}h {m}m"
        block['duration_mins'] = duration_mins
        
        # 2. 时间范围
        try:
            t1 = datetime.strptime(block['start_time_raw'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            t2 = datetime.strptime(block['end_time_raw'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            block['time'] = f"{t1} - {t2}"
        except:
            block['time'] = "??"
            
        # 3. 描述 (取最长的一个子项摘要，或者显示子项数量)
        count = len(block['sub_items'])
        if count > 1:
            block['desc'] = f"包含 {count} 个活动片段"
        else:
            # 只有一个子项，显示其摘要
            item = block['sub_items'][0]
            block['desc'] = item.get('summary') or item.get('window_title') or ""
            
        # 4. Badge
        if block['type'] == 'A':
            block['badge'] = '专注'
            if duration_mins > 60: block['badge'] = 'S级'
        elif block['type'] == 'B':
            block['badge'] = '☕'

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
        
        # 横向布局 (使用 self.timeline_layout 以便动态插入)
        self.timeline_layout = QtWidgets.QHBoxLayout(content)
        self.timeline_layout.setContentsMargins(20, 20, 20, 20)
        self.timeline_layout.setSpacing(5) # 积木间距
        self.timeline_layout.setAlignment(QtCore.Qt.AlignLeft)
        
        # Add Blocks
        self.block_widgets = [] # 存储引用，用于查找
        for block in self.time_blocks:
            w = self._create_block_widget(block)
            self.timeline_layout.addWidget(w)
            self.block_widgets.append(w)
            
        self.timeline_layout.addStretch()
        scroll.setWidget(content)
        parent_layout.addWidget(scroll)

    def _create_block_widget(self, data):
        """根据类型和时长创建横向拉伸的积木"""
        w = QtWidgets.QWidget()
        w.setCursor(QtCore.Qt.PointingHandCursor) # 添加手型光标
        
        # 存储数据，以便点击时使用
        w.block_data = data
        
        # 使用 toggle_block_details 替代 show_block_details
        w.mousePressEvent = lambda e: self.toggle_block_details(w, data) if e.button() == QtCore.Qt.LeftButton else None
        
        # 改为固定宽度，每个事件栏目等大
        w.setFixedWidth(200) 
        
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
            # if width > 60: # 移除宽度检查
            title = QtWidgets.QLabel(f"{data['title']}")
            title.setAlignment(QtCore.Qt.AlignCenter)
            title.setWordWrap(True)
            title.setStyleSheet("color: #1B5E20; font-weight: bold; font-size: 12px; border: none; background: transparent;")
            v_layout.addWidget(title)
            
            # 显示时长 (新增)
            duration_lbl = QtWidgets.QLabel(f"({data['duration_text']})")
            duration_lbl.setAlignment(QtCore.Qt.AlignCenter)
            duration_lbl.setStyleSheet("color: #2E7D32; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            v_layout.addWidget(duration_lbl)
            
            # AI Comment Bubble (Tooltip style inside)
            # if width > 100: # 移除宽度检查
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
            
            # if width > 40: # 移除宽度检查
            lbl = QtWidgets.QLabel("充电")
            lbl.setStyleSheet("color: #795548; font-size: 10px; border: none; background: transparent;")
            v_layout.addWidget(lbl)
            
            # 显示时长 (新增)
            duration_lbl = QtWidgets.QLabel(f"({data['duration_text']})")
            duration_lbl.setAlignment(QtCore.Qt.AlignCenter)
            duration_lbl.setStyleSheet("color: #8D6E63; font-size: 10px; border: none; background: transparent;")
            v_layout.addWidget(duration_lbl)
                
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

    def toggle_block_details(self, block_widget, data):
        """点击 Block 时，在右侧展开详情"""
        # 如果没有子项或只有一个子项，就不展开了
        if len(data.get('sub_items', [])) <= 1:
            return

        # 1. 检查是否已经展开
        if hasattr(self, 'active_detail_widget') and self.active_detail_widget:
            # 如果点击的是同一个，则关闭
            is_same = (self.active_detail_widget.parent_block == block_widget)
            
            # 关闭当前的详情
            self.active_detail_widget.deleteLater()
            self.active_detail_widget = None
            
            if is_same:
                return

        # 2. 创建详情容器
        detail_container = QtWidgets.QWidget()
        detail_container.parent_block = block_widget
        detail_container.setFixedHeight(300) # 与 Block 等高
        detail_container.setStyleSheet("background: transparent;")
        
        # 内部布局：横向排列子项
        h_layout = QtWidgets.QHBoxLayout(detail_container)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.setSpacing(5)
        h_layout.setAlignment(QtCore.Qt.AlignLeft)
        
        # 3. 创建子项积木
        total_width = 0
        for item in data['sub_items']:
            sub_w = self._create_sub_item_widget(item, data['type'])
            h_layout.addWidget(sub_w)
            total_width += (sub_w.width() + 5)
            
        # 设置容器初始宽度为 0 (用于动画)
        detail_container.setFixedWidth(0)
        
        # 4. 插入到父布局中
        # 找到 block_widget 的索引
        idx = self.timeline_layout.indexOf(block_widget)
        if idx >= 0:
            self.timeline_layout.insertWidget(idx + 1, detail_container)
            self.active_detail_widget = detail_container
            
            # 5. 动画展开
            anim = QtCore.QPropertyAnimation(detail_container, b"minimumWidth")
            anim.setDuration(300)
            anim.setStartValue(0)
            anim.setEndValue(total_width + 20) # 加上边距
            anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            
            # 同时动画 maximumWidth 以确保平滑
            anim2 = QtCore.QPropertyAnimation(detail_container, b"maximumWidth")
            anim2.setDuration(300)
            anim2.setStartValue(0)
            anim2.setEndValue(total_width + 20)
            anim2.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            
            self.detail_anim_group = QtCore.QParallelAnimationGroup(self)
            self.detail_anim_group.addAnimation(anim)
            self.detail_anim_group.addAnimation(anim2)
            self.detail_anim_group.start()

    def _create_sub_item_widget(self, item, parent_type):
        """创建子项的小方块"""
        w = QtWidgets.QWidget()
        w.setFixedSize(140, 260) # 比父块稍微矮一点，窄一点
        
        # 样式
        if parent_type == 'A': # 工作学习
            bg_color = "#E8F5E9"
            border_color = "#81C784"
            text_color = "#2E7D32"
        else: # 充电
            bg_color = "#FFFDE7"
            border_color = "#FFF59D"
            text_color = "#F57F17"
            
        w.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px dashed {border_color};
                border-radius: 6px;
            }}
            QWidget:hover {{
                background-color: #FFFFFF;
                border: 1px solid {border_color};
            }}
        """)
        
        v_layout = QtWidgets.QVBoxLayout(w)
        v_layout.setContentsMargins(8, 8, 8, 8)
        
        # 计算时长
        d_min = max(1, int(item['duration'] / 60))
        if d_min < 60:
            d_text = f"{d_min}m"
        else:
            d_text = f"{d_min // 60}h {d_min % 60}m"
            
        # 标题 (进程名或窗口名)
        title_text = item.get('window_title') or item.get('process_name') or "未知"
        # 如果太长截断
        if len(title_text) > 30: title_text = title_text[:28] + "..."
            
        lbl_title = QtWidgets.QLabel(title_text)
        lbl_title.setWordWrap(True)
        lbl_title.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        lbl_title.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        v_layout.addWidget(lbl_title)
        
        # 时长
        lbl_time = QtWidgets.QLabel(d_text)
        lbl_time.setStyleSheet(f"color: {text_color}; font-size: 10px; border: none; background: transparent;")
        v_layout.addWidget(lbl_time)
        
        v_layout.addStretch()
        
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
