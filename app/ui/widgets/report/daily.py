# -*- coding: utf-8 -*-
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
    Signal = QtCore.pyqtSignal

import math
from datetime import datetime, date
import re
from urllib.parse import quote_plus
# from app.data import ActivityHistoryManager
# from app.ui.widgets.report.theme import theme # Removed theme dependency if not used

class SimpleDailyReport(QtWidgets.QWidget):
    """
    New Daily Report with Dashboard and Timeline views.
    """
    clicked = Signal()  # Signal to close

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Data Manager
        # self.history_manager = ActivityHistoryManager()
        
        # Size (Fixed as per request/previous code)
        self.setFixedSize(900, 600)
        
        # Load Data
        self._load_data()
        
        # Build UI
        self._build_ui()
        self._center_on_screen()
        
        # Entry Animation
        self.setWindowOpacity(1.0)

    def _load_data(self):
        """Load data for both dashboard and timeline"""
        self.today = date.today()
        
        # 1. Stats Summary
        summary = {}
        try:
            from app.data.dao.activity_dao import StatsDAO
            summary = StatsDAO.get_daily_summary(self.today) or {}
        except Exception:
            summary = {}

        f_time = summary.get("total_focus_time") or summary.get("focus_time") or 0
        w_time = summary.get("total_work_time") or summary.get("work_time") or 0
        e_time = summary.get("total_entertainment_time") or 0
        total_focus_seconds = int(f_time) + int(w_time)

        self.total_focus_mins = int(total_focus_seconds / 60)
        self.hours = self.total_focus_mins // 60
        self.minutes = self.total_focus_mins % 60
        self.recharged_mins = int(int(e_time) / 60)

        if self.total_focus_mins <= 0:
            self.total_focus_mins = 222
            self.hours = 3
            self.minutes = 42

        self.beat_percentage = min(99, max(1, int(self.total_focus_mins / 4.8)))
        self.peak_flow_mins = 0
        self.willpower_count = 5
        self.efficiency_score = 92

        # 2. Timeline Logs
        self.time_blocks = self._load_timeline_blocks()
        try:
            peak = 0
            for b in self.time_blocks:
                if b.get("type") == "A":
                    peak = max(peak, int(b.get("duration_sec") or 0))
            self.peak_flow_mins = int(peak / 60) if peak > 0 else self.peak_flow_mins
        except Exception:
            pass

    def _load_timeline_blocks(self):
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            sessions = WindowSessionDAO.get_today_sessions()
            if not sessions:
                return self._get_mock_blocks()

            blocks = []
            current_block = None

            for s in sessions:
                status = (s.get("status") or "").lower()
                if status in ["work", "focus"]:
                    s_type = "A"
                    s_title = "\u5de5\u4f5c\u5b66\u4e60"
                elif status == "entertainment":
                    s_type = "B"
                    s_title = "\u5145\u7535"
                else:
                    s_type = "C"
                    s_title = "\u788e\u7247"

                if current_block and current_block["type"] == s_type:
                    current_block["duration_sec"] += int(s.get("duration") or 0)
                    current_block["end_time_raw"] = s.get("end_time") or current_block.get("end_time_raw")
                    current_block["sub_items"].append(s)
                else:
                    if current_block:
                        self._finalize_block(current_block)
                        blocks.append(current_block)

                    current_block = {
                        "type": s_type,
                        "title": s_title,
                        "start_time_raw": s.get("start_time"),
                        "end_time_raw": s.get("end_time"),
                        "duration_sec": int(s.get("duration") or 0),
                        "sub_items": [s],
                    }

            if current_block:
                self._finalize_block(current_block)
                blocks.append(current_block)

            return blocks
        except Exception as e:
            print(f"Error processing blocks: {e}")
            return self._get_mock_blocks()

    def _get_mock_blocks(self):
        """Generate mock blocks for visualization when no data exists"""
        return [
            {
                "time_label": "09:00",
                "duration_text": "3m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60", # "??????"
                "desc": "09:00",
                "category": "study",
                "duration_sec": 180,
                "sub_items": [{}, {}]
            },
            {
                "time_label": "09:03",
                "duration_text": "2m",
                "type": "B",
                "title": "\u5145\u7535", # "???"
                "desc": "09:03",
                "category": "break",
                "duration_sec": 120,
                "sub_items": [{}]
            },
            {
                "time_label": "09:05",
                "duration_text": "6m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60",
                "desc": "09:05",
                "category": "study",
                "duration_sec": 360,
                "sub_items": [{}]
            },
            {
                "time_label": "09:11",
                "duration_text": "2m",
                "type": "B",
                "title": "\u5145\u7535",
                "desc": "09:11",
                "category": "break",
                "duration_sec": 120,
                "sub_items": [{}]
            },
            {
                "time_label": "09:13",
                "duration_text": "2m",
                "type": "B",
                "title": "\u5145\u7535",
                "desc": "09:13",
                "category": "break",
                "duration_sec": 120,
                "sub_items": [{}]
            },
            {
                "time_label": "09:15",
                "duration_text": "6m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60",
                "desc": "09:15",
                "category": "study",
                "duration_sec": 360,
                "sub_items": [{}, {}, {}]
            }
        ]

    def _session_category(self, session: dict) -> str:
        proc = (session.get("process_name") or "").lower()
        title = (session.get("window_title") or "") + " " + (session.get("summary") or "")
        t = title.lower()

        short_video_keys = [
            "douyin", "\u6296\u97f3", "tiktok", "kuaishou", "\u5feb\u624b", "youtube",
            "bilibili", "\u54d4\u54e9\u54d4\u54e9", "\u817e\u8baf\u89c6\u9891", "\u7231\u5947\u827a", "iqiyi",
        ]
        game_keys = [
            "steam", "epic", "genshin", "\u539f\u795e", "league", "lol", "valorant", "\u6e38\u620f", "taptap",
        ]
        study_keys = [
            "leetcode", "\u529b\u6263", "\u725b\u5ba2", "csdn", "github", "stackoverflow", "wikipedia",
            "\u6162\u5b66", "\u5b66\u4e60", "docs", "notion", "\u6559\u7a0b", "\u8bfe\u7a0b", "\u6162\u8bfb",
        ]

        if any(k in t for k in short_video_keys):
            return "short_video"
        if any(k in t for k in game_keys) or proc in ["steam.exe", "epicgameslauncher.exe"]:
            return "game"
        if any(k in t for k in study_keys):
            return "study"

        if proc in ["chrome.exe", "msedge.exe", "firefox.exe"]:
            return "web_other"
        if proc in ["pycharm64.exe", "idea64.exe", "code.exe"]:
            return "study"
        return "other"

    def _block_category(self, block: dict) -> str:
        if block.get("type") == "B":
            return "break"
        scores = {}
        for s in block.get("sub_items") or []:
            cat = self._session_category(s or {})
            dur = int((s or {}).get("duration") or 0)
            scores[cat] = scores.get(cat, 0) + max(1, dur)
        if not scores:
            return "study" if block.get("type") == "A" else "other"
        return max(scores.items(), key=lambda kv: kv[1])[0]

    def _finalize_block(self, block):
        # Calculate display properties
        duration_mins = max(1, int(block['duration_sec'] / 60))
        block['duration_text'] = f"{duration_mins}m" if duration_mins < 60 else f"{duration_mins // 60}h {duration_mins % 60}m"
        
        try:
            t1 = datetime.strptime(block['start_time_raw'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            # t2 = datetime.strptime(block['end_time_raw'], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
            block['time_label'] = t1
        except:
            block['time_label'] = ""
            
        def _parse_dt(v: str):
            if not v:
                return None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    return datetime.strptime(v, fmt)
                except Exception:
                    pass
            return None

        start_dt = _parse_dt(block.get("start_time_raw"))
        if start_dt:
            block["desc"] = start_dt.strftime("%H:%M")
        else:
            block["desc"] = block.get("time_label") or ""

        block["category"] = block.get("category") or self._block_category(block)
        details = []
        for s in block.get("sub_items") or []:
            if not isinstance(s, dict):
                continue
            details.append({
                "window_title": s.get("window_title") or "",
                "process_name": s.get("process_name") or "",
                "summary": s.get("summary") or "",
                "status": s.get("status") or "",
                "duration": int(s.get("duration") or 0),
                "start_time": s.get("start_time") or "",
                "end_time": s.get("end_time") or "",
            })
        block["details"] = details

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with border radius
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            QWidget#MainContainer {
                background: qradialgradient(cx:0.5, cy:0.5, radius: 1.0, fx:0.5, fy:0.5, stop:0 #E8F5E9, stop:0.6 #C8E6C9, stop:1 #81C784);
                border-radius: 20px;
                border: 2px solid #66BB6A;
            }
        """)
        main_layout.addWidget(self.container)
        
        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked Widget for Views
        self.stack = QtWidgets.QStackedWidget()
        
        # View 1: Dashboard
        self.dashboard_view = DailyDashboard(self)
        self.stack.addWidget(self.dashboard_view)
        
        # View 2: Timeline
        self.timeline_view = DailyTimeline(self)
        self.stack.addWidget(self.timeline_view)
        
        container_layout.addWidget(self.stack)
        
        # Connect signals
        self.dashboard_view.switch_to_timeline.connect(lambda: self.stack.setCurrentWidget(self.timeline_view))
        self.timeline_view.back_to_summary.connect(lambda: self.stack.setCurrentWidget(self.dashboard_view))
        self.dashboard_view.close_req.connect(self.close)
        self.timeline_view.close_req.connect(self.close)

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


class DailyDashboard(QtWidgets.QWidget):
    switch_to_timeline = Signal()
    close_req = Signal()

    def __init__(self, parent_report):
        super().__init__()
        self.report = parent_report
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self._build_header(layout)
        
        # Content
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(20)
        
        # Left: Energy Compass
        self._build_left_panel(content_layout)
        
        # Right: Data Matrix
        self._build_right_panel(content_layout)
        
        layout.addWidget(content_widget)

    def _build_header(self, parent_layout):
        header = QtWidgets.QWidget()
        header.setFixedHeight(70) # Increased height
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 0)
        
        # Back
        btn_back = QtWidgets.QPushButton("< \u8fd4\u56de") # "< 返回"
        btn_back.setCursor(QtCore.Qt.PointingHandCursor)
        btn_back.setStyleSheet("color: #50795D; font-weight: bold; border: none; font-size: 16px;") # Larger font
        btn_back.clicked.connect(self.close_req.emit)
        
        # Date
        lbl_date = QtWidgets.QLabel(date.today().strftime("%Y.%m.%d %A"))
        lbl_date.setStyleSheet("color: #2E4E3F; font-size: 20px; font-weight: bold;") # Larger font
        
        # Switch
        btn_switch = QtWidgets.QPushButton("\u5207\u6362\u5230\u65f6\u95f4\u8f74 >") # "切换到时间轴 >"
        btn_switch.setCursor(QtCore.Qt.PointingHandCursor)
        btn_switch.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #50795D;
                border: 2px solid #50795D;
                border-radius: 18px;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E8F5E9;
            }
        """)
        btn_switch.clicked.connect(self.switch_to_timeline.emit)
        
        h_layout.addWidget(btn_back)
        h_layout.addStretch()
        h_layout.addWidget(lbl_date)
        h_layout.addStretch()
        h_layout.addWidget(btn_switch)
        
        parent_layout.addWidget(header)

    def _build_left_panel(self, parent_layout):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #E8F5E9;
                border-radius: 20px;
            }
        """)
        # Create a custom paint widget for the ring
        v_layout = QtWidgets.QVBoxLayout(panel)
        v_layout.setContentsMargins(25, 25, 25, 25)
        
        # Header text
        top_row = QtWidgets.QHBoxLayout()
        t1 = QtWidgets.QLabel("\ud83c\udfaf \u4eca\u65e5\u76ee\u6807\u8fdb\u5ea6") # "? ??????????"
        t1.setStyleSheet("color: #2E7D32; font-weight: bold; font-size: 16px; background: transparent;")
        t2 = QtWidgets.QLabel("45%")
        t2.setStyleSheet("color: #2E7D32; font-weight: bold; font-size: 20px; background: transparent;")
        top_row.addWidget(t1)
        top_row.addStretch()
        top_row.addWidget(t2)
        v_layout.addLayout(top_row)
        
        v_layout.addStretch()
        
        # Ring Widget
        ring = ProgressRingWidget(percentage=0.45, center_text=f"{self.report.hours}\u5c0f\u65f6{self.report.minutes}\u5206", sub_text="\u4eca\u65e5\u4e13\u6ce8\u80fd\u91cf") # "???", "??", "??????????"
        v_layout.addWidget(ring, 0, QtCore.Qt.AlignCenter)
        
        v_layout.addStretch()
        
        # Stats footer
        f1 = QtWidgets.QLabel(f"\ud83c\udfc6 \u51fb\u8d25\u5168\u56fd {self.report.beat_percentage}% \u7684\u7528\u6237") # "? ???????", "?????"
        f1.setAlignment(QtCore.Qt.AlignCenter)
        f1.setStyleSheet("color: #1B5E20; font-size: 15px; font-weight: bold; background: transparent;")
        
        f2 = QtWidgets.QLabel("\u72b6\u6001: \ud83d\udfe2 \u6df1\u5ea6\u6c89\u6d78\u4e2d...") # "??: ? ????????..."
        f2.setAlignment(QtCore.Qt.AlignCenter)
        f2.setStyleSheet("color: #2E7D32; font-size: 14px; font-weight: bold; background: #C8E6C9; border-radius: 12px; padding: 6px 12px; margin-top: 10px;")
        
        v_layout.addWidget(f1)
        v_layout.addWidget(f2)
        
        parent_layout.addWidget(panel, 1) # Stretch factor 1

    def _build_right_panel(self, parent_layout):
        right_container = QtWidgets.QWidget()
        v_layout = QtWidgets.QVBoxLayout(right_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(20)
        
        # Grid for 4 cards
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(20)
        
        # Card 1: Peak Flow
        c1 = StatCard("\u5dc5\u5cf0\u5fc3\u6d41", f"{self.report.peak_flow_mins}", "\u5206\u949f", "\u26a1", "#F0F4C3", "#827717")
        # Card 2: Willpower
        c2 = StatCard("\u610f\u5fd7\u529b", f"{self.report.willpower_count}", "\u6b21\u6210\u529f", "\ud83d\udee1\ufe0f", "#FFECB3", "#FF6F00")
        # Card 3: Recharged
        c3 = StatCard("\u5df2\u5145\u80fd", f"{self.report.recharged_mins}", "\u5206\u949f", "\ud83d\udd0b", "#DCEDC8", "#33691E")
        # Card 4: Efficiency
        c4 = StatCard("\u6548\u80fd\u6307\u6570", f"{self.report.efficiency_score}", "\u5206", "\ud83d\udcc8", "#FFCCBC", "#BF360C")
        
        # Set minimum height for cards to make them prominent
        for c in [c1, c2, c3, c4]:
            c.setMinimumHeight(110)
        
        grid.addWidget(c1, 0, 0)
        grid.addWidget(c2, 0, 1)
        grid.addWidget(c3, 1, 0)
        grid.addWidget(c4, 1, 1)
        
        # Add grid with higher stretch factor to take up more space
        v_layout.addLayout(grid, 3)
        
        # Communication Box
        comm_box = QtWidgets.QWidget()
        comm_box.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            border: 2px solid #C8E6C9;
        """)
        # Shrink the comm box by setting a fixed or max height
        comm_box.setMaximumHeight(140) 
        
        comm_layout = QtWidgets.QVBoxLayout(comm_box)
        comm_layout.setContentsMargins(20, 15, 20, 15) # Slightly reduced margins
        
        title = QtWidgets.QLabel("\ud83d\udcac \u5854\u53f0\u901a\u8baf (\u5b9e\u65f6\u64ad\u62a5)")
        title.setStyleSheet("color: #455A64; font-weight: 900; font-size: 14px; border: none;") # Bolder
        
        msg = QtWidgets.QLabel('"\u68c0\u6d4b\u5230\u5f3a\u5927\u7684\u610f\u5fd7\u529b\u6ce2\u52a8\uff01\n\u4f60\u5df2\u6210\u529f\u62e6\u622a5\u6b21\u5e72\u6270\u3002" (Mock)')
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #37474F; font-size: 13px; font-weight: bold; margin-top: 5px; border: none; line-height: 1.4;") # Bolder, smaller text
        
        comm_layout.addWidget(title)
        comm_layout.addWidget(msg)
        comm_layout.addStretch()
        
        # Add comm box with lower stretch factor
        v_layout.addWidget(comm_box, 1)
        
        parent_layout.addWidget(right_container, 1)


class ProgressRingWidget(QtWidgets.QWidget):
    def __init__(self, percentage=0.45, center_text="", sub_text=""):
        super().__init__()
        self.percentage = percentage
        self.center_text = center_text
        self.sub_text = sub_text
        self.setFixedSize(220, 220)
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect().adjusted(10, 10, -10, -10)
        
        # Draw Background Ring
        pen = QtGui.QPen(QtGui.QColor("#C8E6C9"), 18) # Thicker ring
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        
        # Draw Progress Ring
        pen.setColor(QtGui.QColor("#43A047"))
        painter.setPen(pen)
        # Angle is in 1/16th of a degree. Start at 90 (top) -> 90*16 = 1440
        # Span is negative for clockwise.
        span_angle = int(-self.percentage * 360 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)
        
        # Draw Tree (Text for now)
        painter.setPen(QtCore.Qt.NoPen)
        font = QtGui.QFont()
        font.setPixelSize(70) # Larger icon
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#2E7D32"))
        painter.drawText(rect.adjusted(0, -50, 0, 0), QtCore.Qt.AlignCenter, "\ud83c\udf33") # "?"
        
        # Draw Center Text
        font.setPixelSize(32) # Larger text
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#1B5E20"))
        painter.drawText(rect.adjusted(0, 50, 0, 0), QtCore.Qt.AlignCenter, self.center_text)
        
        font.setPixelSize(14) # Larger sub text
        font.setBold(True) # Bolder
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#388E3C"))
        painter.drawText(rect.adjusted(0, 85, 0, 0), QtCore.Qt.AlignCenter, self.sub_text)


class StatCard(QtWidgets.QFrame):
    def __init__(self, title, value, unit, icon, bg_color, text_color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 16px;
            }}
        """)
        
        # Main Layout (Horizontal: Icon | Content)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Icon Area
        lbl_icon = QtWidgets.QLabel(icon)
        lbl_icon.setStyleSheet("background: transparent; font-size: 36px;") # Big Icon
        lbl_icon.setAlignment(QtCore.Qt.AlignCenter)
        lbl_icon.setFixedSize(50, 50)
        
        # Content Area
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setSpacing(5)
        
        l_title = QtWidgets.QLabel(title)
        l_title.setStyleSheet(f"color: {text_color}; font-size: 15px; font-weight: 800; background: transparent; opacity: 0.9;") # Bolder
        
        # Value + Unit Row
        val_layout = QtWidgets.QHBoxLayout()
        val_layout.setSpacing(8)
        val_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)
        
        l_val = QtWidgets.QLabel(value)
        l_val.setStyleSheet(f"color: {text_color}; font-size: 32px; font-weight: 900; background: transparent;") # Bolder & Larger
        
        l_unit = QtWidgets.QLabel(unit)
        l_unit.setStyleSheet(f"color: {text_color}; font-size: 14px; font-weight: 800; padding-bottom: 6px; background: transparent; opacity: 0.8;") # Bolder
        
        val_layout.addWidget(l_val)
        val_layout.addWidget(l_unit)
        val_layout.addStretch()
        
        content_layout.addWidget(l_title)
        content_layout.addLayout(val_layout)
        
        layout.addWidget(lbl_icon)
        layout.addLayout(content_layout)



class DailyTimeline(QtWidgets.QWidget):
    back_to_summary = Signal()
    close_req = Signal()

    def __init__(self, parent_report):
        super().__init__()
        self.report = parent_report
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EAF4EE, stop:0.55 #D7EADF, stop:1 #BFDCCD);
            }
        """)
        
        # Header
        self._build_header(layout)
        
        # Scroll Area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.viewport().setStyleSheet("background: transparent;")
        
        # Styled scrollbar
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:horizontal {
                border: none;
                background: rgba(255,255,255,160);
                height: 10px;
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(90, 140, 115, 180);
                min-width: 48px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)
        
        # Timeline Container
        self.timeline_container = TimelineContainer(self.report.time_blocks)
        scroll.setWidget(self.timeline_container)
        
        layout.addWidget(scroll)

    def _build_header(self, parent_layout):
        header = QtWidgets.QWidget()
        header.setFixedHeight(70)
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_back = QtWidgets.QPushButton("< \u8fd4\u56de") # "< 返回"
        btn_back.setCursor(QtCore.Qt.PointingHandCursor)
        btn_back.setStyleSheet("color: #50795D; font-weight: bold; border: none; font-size: 16px;")
        btn_back.clicked.connect(self.close_req.emit)
        
        lbl_date = QtWidgets.QLabel(date.today().strftime("%Y.%m.%d %A"))
        lbl_date.setStyleSheet("color: #2E4E3F; font-size: 16px; font-weight: bold;")
        
        btn_summary = QtWidgets.QPushButton("[ < \u56de\u5230\u4eca\u65e5\u603b\u7ed3 ]") # "[ < 回到今日总结 ]"
        btn_summary.setCursor(QtCore.Qt.PointingHandCursor)
        btn_summary.setStyleSheet("color: #50795D; font-weight: bold; border: none; font-size: 14px;")
        btn_summary.clicked.connect(self.back_to_summary.emit)
        
        h_layout.addWidget(btn_back)
        h_layout.addStretch()
        h_layout.addWidget(lbl_date)
        h_layout.addStretch()
        h_layout.addWidget(btn_summary)
        
        parent_layout.addWidget(header)


class TimelineContainer(QtWidgets.QWidget):
    def __init__(self, blocks):
        super().__init__()
        self.blocks = blocks
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._padding_x = 90
        self._slot_w = 210
        self._y_center = 190
        self._card_w = 170
        self._card_h = 92
        self._node_size = 18
        self._gap_node_to_card = 18
        self._gap_desc_to_line = 14

        self._items = []
        for i, block in enumerate(self.blocks):
            is_top = (block.get("type") == "A")
            item = TimelineItemWidget(self, block, is_top)
            self._items.append(item)

        total_w = self._padding_x * 2 + max(1, len(self._items)) * self._slot_w
        self.setFixedSize(total_w, 380)
        self._layout_items()

    def _layout_items(self):
        for idx, item in enumerate(self._items):
            slot_x = self._padding_x + idx * self._slot_w
            node_x = int(slot_x + (self._slot_w / 2) - (self._node_size / 2))
            node_y = int(self._y_center - (self._node_size / 2))
            card_x = int(slot_x + (self._slot_w / 2) - (self._card_w / 2))
            if item.is_top:
                card_y = int(node_y - self._gap_node_to_card - self._card_h)
                desc_y = int(self._y_center + self._gap_desc_to_line)
            else:
                card_y = int(node_y + self._gap_node_to_card + self._node_size)
                desc_y = int(card_y + self._card_h + 10)

            item.setGeometry(card_x, 0, self._card_w, self.height())
            item.place(card_x, card_y, node_x, node_y, desc_y, self._card_w, self._card_h, self._node_size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        y_center = self._y_center

        glow = QtGui.QPen(QtGui.QColor(120, 200, 160, 90), 14)
        glow.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(glow)
        painter.drawLine(0, y_center, self.width(), y_center)

        main = QtGui.QPen(QtGui.QColor(95, 165, 130, 210), 6)
        main.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(main)
        painter.drawLine(0, y_center, self.width(), y_center)

        font = QtGui.QFont()
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(25, 55, 45, 190))
        painter.drawText(QtCore.QRectF(20, 40, 200, 24), QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "09:00")
        
        # Motivational quotes instead of "Now XX:XX"
        quotes = ["\u575a\u6301\u5c31\u662f\u80dc\u5229", "\u6bcf\u4e00\u523b\u90fd\u503c\u5f97", "\u4fdd\u6301\u4e13\u6ce8", "\u672a\u6765\u53ef\u671f", "\u52a0\u6cb9\uff01"] # "坚持就是胜利", "每一刻都值得", "保持专注", "未来可期", "加油！"
        import random
        quote = quotes[int(datetime.now().timestamp()) % len(quotes)]
        
        painter.drawText(QtCore.QRectF(self.width() - 240, 40, 220, 24), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, quote)

        for item in self._items:
            node_center = item.node_center()
            if node_center is None:
                continue
            x, y = node_center
            if item.is_top:
                tip_y = item.card_tip_y()
            else:
                tip_y = item.card_tip_y()
            pen = QtGui.QPen(item.connector_color(), 3)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(x, y, x, tip_y)


class BubbleCard(QtWidgets.QWidget):
    clicked = Signal(object)
    hoverChanged = Signal(bool)

    def __init__(self, data, is_top):
        super().__init__()
        self.data = data
        self.is_top = is_top
        self.setFixedSize(140, 100) # Slightly taller for the tip
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        category = (data.get("category") or ("break" if data.get("type") == "B" else "other")).lower()
        if data.get("type") == "B":
            category = "break"

        palettes = {
            "study": ("#BFE7D2", "#173628", "#173628", (85, 160, 125, 150)),
            "short_video": ("#E7E2FA", "#2A2453", "#2A2453", (150, 125, 210, 150)),
            "game": ("#FFE5D9", "#4E2B1F", "#4E2B1F", (230, 120, 90, 150)),
            "web_other": ("#DDEFF7", "#163041", "#163041", (90, 150, 180, 140)),
            "other": ("#CFE5D7", "#173628", "#173628", (85, 160, 125, 120)),
            "break": ("#FBF3E7", "#3E2723", "#3E2723", (210, 175, 120, 140)),
        }
        bg, text, icon, border_rgba = palettes.get(category, palettes["other"])
        self.bg_color = QtGui.QColor(bg)
        self.text_color = QtGui.QColor(text)
        self.icon_color = QtGui.QColor(icon)
        self.border_color = QtGui.QColor(*border_rgba)
        self._category = category

        self._shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(14)
        self._shadow.setOffset(0, 5)
        self._shadow.setColor(QtGui.QColor(0, 0, 0, 40))
        self.setGraphicsEffect(self._shadow)
        self._shadow_blur_anim = QtCore.QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._shadow_off_anim = QtCore.QPropertyAnimation(self._shadow, b"yOffset", self)
        self._shadow_blur_anim.setDuration(160)
        self._shadow_off_anim.setDuration(160)
        self._shadow_blur_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._shadow_off_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._hovered = False

    def tip_apex_y(self):
        return 90 if self.is_top else 0

    def enterEvent(self, event):
        self._hovered = True
        self.hoverChanged.emit(True)
        self._shadow_blur_anim.stop()
        self._shadow_off_anim.stop()
        self._shadow_blur_anim.setStartValue(self._shadow.blurRadius())
        self._shadow_blur_anim.setEndValue(26)
        self._shadow_off_anim.setStartValue(self._shadow.yOffset())
        self._shadow_off_anim.setEndValue(10)
        self._shadow_blur_anim.start()
        self._shadow_off_anim.start()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.hoverChanged.emit(False)
        self._shadow_blur_anim.stop()
        self._shadow_off_anim.stop()
        self._shadow_blur_anim.setStartValue(self._shadow.blurRadius())
        self._shadow_blur_anim.setEndValue(14)
        self._shadow_off_anim.setStartValue(self._shadow.yOffset())
        self._shadow_off_anim.setEndValue(5)
        self._shadow_blur_anim.start()
        self._shadow_off_anim.start()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Rect for the box
        rect_h = 80
        tip_h = 10
        tip_w = 20
        
        path = QtGui.QPainterPath()
        
        if self.is_top:
            # Box at top, tip at bottom
            rect = QtCore.QRectF(0, 0, self.width(), rect_h)
            tip_y = rect_h
            tip_x = self.width() / 2
            
            path.addRoundedRect(rect, 15, 15)
            # Triangle pointing down
            path.moveTo(tip_x - 10, tip_y)
            path.lineTo(tip_x, tip_y + tip_h)
            path.lineTo(tip_x + 10, tip_y)
            path.closeSubpath()
        else:
            # Box at bottom, tip at top
            rect = QtCore.QRectF(0, tip_h, self.width(), rect_h)
            tip_y = tip_h
            tip_x = self.width() / 2
            
            path.addRoundedRect(rect, 15, 15)
            # Triangle pointing up
            path.moveTo(tip_x - 10, tip_y)
            path.lineTo(tip_x, tip_y - tip_h)
            path.lineTo(tip_x + 10, tip_y)
            path.closeSubpath()

        shadow = QtGui.QColor(0, 0, 0, 26 if not self._hovered else 34)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(shadow)
        painter.drawPath(path.translated(2.0, 3.0))
        
        # Draw BG
        pen = QtGui.QPen(self.border_color, 1.2 if not self._hovered else 2.1)
        painter.setPen(pen)
        if self._hovered:
            c = QtGui.QColor(self.bg_color)
            c = c.lighter(106)
            painter.setBrush(c)
        else:
            painter.setBrush(self.bg_color)
        painter.drawPath(path)
        
        painter.setPen(self.text_color)
        
        # Icon
        y_offset = 0 if self.is_top else tip_h
        
        icon_rect = QtCore.QRectF(10, 10 + y_offset, 30, 30)
        font = QtGui.QFont()
        font.setPixelSize(20)
        painter.setFont(font)
        icon_char = "\ud83c\udf33" if self.data['type'] == 'A' else "\u2615" # Tree vs Coffee
        painter.setPen(self.icon_color)
        painter.drawText(icon_rect, QtCore.Qt.AlignCenter, icon_char)
        painter.setPen(self.text_color)
        
        # Title
        title_rect = QtCore.QRectF(45, 15 + y_offset, 90, 20)
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(title_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.data['title'])
        
        # Duration
        dur_rect = QtCore.QRectF(45, 35 + y_offset, 90, 30)
        font.setPixelSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(dur_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.data['duration_text'])

class TimelineItemWidget(QtWidgets.QWidget):
    def __init__(self, parent, block_data, is_top):
        super().__init__(parent)
        self.block_data = block_data
        self.is_top = is_top
        self._card = BubbleCard(block_data, is_top)
        self._desc = QtWidgets.QLabel(block_data.get("desc", ""))
        self._desc.setAlignment(QtCore.Qt.AlignCenter)
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: rgba(20, 40, 35, 210); font-size: 12px; font-weight: 800; background: transparent;")

        is_rest = (block_data.get("type") == "B")
        self._node = TimelineNode("#FFD54F" if is_rest else "#6CBF9C", is_rest)

        self._card.setParent(self)
        self._desc.setParent(self)
        self._node.setParent(self)

        self._node_pos = None
        self._card_tip_y = None
        self._base_card_y = 0
        self._base_node_y = 0
        self._card_anim = QtCore.QPropertyAnimation(self._card, b"pos", self)
        self._card_anim.setDuration(160)
        self._card_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._card.clicked.connect(self._show_details)
        self._card.hoverChanged.connect(self._set_hover)
        self._popup = None

    def place(self, card_x, card_y, node_x, node_y, desc_y, card_w, card_h, node_size):
        self._card.setFixedSize(card_w, card_h + 12)
        self._card.move(0, card_y)
        self._node.setFixedSize(node_size, node_size)
        self._node.move(node_x - self.x(), node_y)
        self._desc.setFixedWidth(card_w + 20)
        self._desc.move(int((card_w - self._desc.width()) / 2), desc_y)

        self._card_tip_y = card_y + self._card.tip_apex_y()
        self._base_card_y = card_y
        self._base_node_y = node_y

        self._node_pos = (node_x + int(node_size / 2), node_y + int(node_size / 2))
        self.update()

    def node_center(self):
        return self._node_pos

    def card_tip_y(self):
        return self._card_tip_y

    def connector_color(self):
        if self.block_data.get("type") == "B":
            return QtGui.QColor(255, 214, 79, 220)
        return QtGui.QColor(108, 191, 156, 220)

    def _set_hover(self, hovered: bool):
        offset = -8 if self.is_top else 8
        target_y = self._base_card_y + (offset if hovered else 0)
        self._card_anim.stop()
        self._card_anim.setStartValue(self._card.pos())
        self._card_anim.setEndValue(QtCore.QPoint(0, target_y))
        self._card_anim.start()
        self._node.set_hover(hovered)

    def _show_details(self, data: dict):
        if self._popup and self._popup.isVisible():
            self._popup.close()
        self._popup = TimelineDetailPopup(self.window(), data)
        self._popup.adjustSize()
        if self.is_top:
            anchor = self._card.mapToGlobal(QtCore.QPoint(self._card.width() // 2, self._card.height()))
            x = anchor.x() - self._popup.width() // 2
            y = anchor.y() + 10
        else:
            anchor = self._card.mapToGlobal(QtCore.QPoint(self._card.width() // 2, 0))
            x = anchor.x() - self._popup.width() // 2
            y = anchor.y() - self._popup.height() - 10
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left() + 10, min(x, geo.right() - self._popup.width() - 10))
            y = max(geo.top() + 10, min(y, geo.bottom() - self._popup.height() - 10))
        else:
            x = max(10, x)
            y = max(10, y)
        self._popup.move(x, y)
        self._popup.show()

class TimelineNode(QtWidgets.QWidget):
    def __init__(self, color, is_hollow):
        super().__init__()
        self.color = color
        self.is_hollow = is_hollow
        self.setFixedSize(18, 18)
        self._hovered = False

    def set_hover(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        if not self.is_hollow:
            glow_color = QtGui.QColor(self.color)
            glow_color.setAlpha(150 if self._hovered else 100)
            painter.setBrush(glow_color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(self.rect())
            
            painter.setBrush(QtGui.QColor(self.color))
            painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))
        else:
            glow_color = QtGui.QColor(self.color)
            glow_color.setAlpha(150 if self._hovered else 100)
            painter.setBrush(glow_color)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(self.rect())
            
            painter.setBrush(QtGui.QColor("#FFFFFF"))
            painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))
            
            pen = QtGui.QPen(QtGui.QColor(self.color), 2.2 if self._hovered else 2.0)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))


class TimelineDetailPopup(QtWidgets.QFrame):
    def __init__(self, parent, block_data: dict):
        super().__init__(parent, QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self._block_data = block_data or {}
        self._shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(26)
        self._shadow.setOffset(0, 10)
        self._shadow.setColor(QtGui.QColor(0, 0, 0, 45))
        self.setGraphicsEffect(self._shadow)
        self._build()

    def _category_color(self) -> QtGui.QColor:
        cat = (self._block_data.get("category") or "other").lower()
        colors = {
            "study": QtGui.QColor(108, 191, 156),
            "short_video": QtGui.QColor(150, 125, 210),
            "game": QtGui.QColor(230, 120, 90),
            "web_other": QtGui.QColor(90, 150, 180),
            "break": QtGui.QColor(255, 214, 79),
            "other": QtGui.QColor(108, 191, 156),
        }
        return colors.get(cat, colors["other"])

    def _fmt_hm(self, dt_str: str) -> str:
        if not dt_str:
            return "--:--"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(dt_str, fmt).strftime("%H:%M")
            except Exception:
                pass
        try:
            return dt_str[-8:-3]
        except Exception:
            return "--:--"

    def _guess_url(self, d: dict) -> str:
        text = " ".join([
            str(d.get("window_title") or ""),
            str(d.get("summary") or ""),
            str(d.get("process_name") or ""),
        ])
        m = re.search(r"(https?://[\\w\\-\\.]+(?:\\:[0-9]+)?(?:/[\\w\\-\\._~:/?#[\\]@!$&'()*+,;=%]*)?)", text)
        if m:
            return m.group(1)
        t = text.lower()
        mapping = [
            ("bilibili", "https://www.bilibili.com/"),
            ("\u54d4\u54e9\u54d4\u54e9", "https://www.bilibili.com/"),
            ("douyin", "https://www.douyin.com/"),
            ("\u6296\u97f3", "https://www.douyin.com/"),
            ("tiktok", "https://www.tiktok.com/"),
            ("youtube", "https://www.youtube.com/"),
            ("steam", "https://store.steampowered.com/"),
            ("github", "https://github.com/"),
            ("leetcode", "https://leetcode.com/"),
            ("\u529b\u6263", "https://leetcode.cn/"),
            ("csdn", "https://www.csdn.net/"),
            ("stackoverflow", "https://stackoverflow.com/"),
            ("wikipedia", "https://wikipedia.org/"),
        ]
        for k, url in mapping:
            if k in t:
                return url
        query = (d.get("summary") or d.get("window_title") or "").strip()
        if not query:
            query = t.strip()
        if query:
            return f"https://www.bing.com/search?q={quote_plus(query[:80])}"
        return ""

    def _build(self):
        accent = self._category_color()
        # Ensure accent color is visible on light background
        accent_rgb = f"{accent.red()}, {accent.green()}, {accent.blue()}"
        
        self.setStyleSheet(f"""
            QFrame#PopupRoot {{
                background: #FFF9E6; /* Light cream background */
                border: 2px solid rgba({accent_rgb}, 180);
                border-radius: 20px;
            }}
            QLabel {{ background: transparent; }}
            QPushButton#LinkBtn {{
                border: 1px solid rgba({accent_rgb}, 150);
                border-radius: 12px;
                padding: 6px 12px;
                color: rgba(40, 60, 20, 240);
                background: rgba(255, 255, 255, 180);
                font-weight: 800;
                font-size: 12px;
            }}
            QPushButton#LinkBtn:hover {{
                background: rgba({accent_rgb}, 40);
                color: rgba(20, 40, 10, 255);
            }}
            QPushButton#CloseBtn {{
                border: none;
                background: rgba({accent_rgb}, 30);
                border-radius: 12px;
                color: rgba(40, 60, 20, 220);
                font-size: 16px;
                font-weight: 900;
            }}
            QPushButton#CloseBtn:hover {{
                background: rgba({accent_rgb}, 60);
                color: rgba(20, 40, 10, 255);
            }}
        """)
        self.setObjectName("PopupRoot")
        self.setMinimumWidth(360)
        self.setMaximumWidth(420)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(10)
        dot = QtWidgets.QLabel(" ")
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: rgba({accent.red()}, {accent.green()}, {accent.blue()}, 220); border-radius: 5px;")
        title = QtWidgets.QLabel("\u64cd\u4f5c\u7ec6\u8282")
        title.setStyleSheet("color: rgba(20, 50, 40, 235); font-size: 13px; font-weight: 900;")
        close_btn = QtWidgets.QPushButton("\u00d7")
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.close)
        header.addWidget(dot)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        meta = QtWidgets.QLabel(f"{self._block_data.get('title','')}  \u00b7  {self._block_data.get('duration_text','')}")
        meta.setStyleSheet("color: rgba(30, 60, 50, 190); font-size: 12px; font-weight: 700;")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        sep = QtWidgets.QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: rgba({accent.red()}, {accent.green()}, {accent.blue()}, 70); border: none;")
        layout.addWidget(sep)

        details = self._block_data.get("details") or []
        if not details:
            empty = QtWidgets.QLabel("\u6682\u65e0\u66f4\u591a\u6570\u636e")
            empty.setStyleSheet("color: rgba(40, 70, 60, 170); font-size: 12px;")
            layout.addWidget(empty)
            return

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.viewport().setStyleSheet("background: transparent;")

        body = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        for d in details[:12]:
            v.addWidget(TimelineDetailRow(d, accent, self._fmt_hm, self._guess_url))
        v.addStretch()

        scroll.setWidget(body)
        scroll.setFixedHeight(min(260, max(120, 28 + len(details[:12]) * 54)))
        layout.addWidget(scroll)


class TimelineDetailRow(QtWidgets.QFrame):
    def __init__(self, detail: dict, accent: QtGui.QColor, fmt_hm, guess_url):
        super().__init__()
        self._detail = detail or {}
        self._accent = accent
        self._fmt_hm = fmt_hm
        self._guess_url = guess_url
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, 180);
                border: 1px solid rgba({self._accent.red()}, {self._accent.green()}, {self._accent.blue()}, 100);
                border-radius: 14px;
            }}
        """)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title_text = (self._detail.get("summary") or self._detail.get("window_title") or "").strip()
        if not title_text:
            title_text = "\u672a\u77e5\u7a97\u53e3"

        title = QtWidgets.QLabel()
        title.setStyleSheet("color: rgba(20, 50, 40, 230); font-size: 12px; font-weight: 800;")
        title.setWordWrap(False)
        fm = QtGui.QFontMetrics(title.font())
        title.setText(fm.elidedText(title_text, QtCore.Qt.ElideRight, 320))
        layout.addWidget(title)

        start = self._fmt_hm(self._detail.get("start_time") or "")
        end = self._fmt_hm(self._detail.get("end_time") or "")
        dur = int(self._detail.get("duration") or 0)
        mins = max(1, int(dur / 60))
        process_name = (self._detail.get("process_name") or "").strip()
        sub = QtWidgets.QLabel(f"{start} - {end}  \u00b7  {mins}m  \u00b7  {process_name}")
        sub.setStyleSheet("color: rgba(30, 60, 50, 175); font-size: 11px; font-weight: 700;")
        sub.setWordWrap(False)
        layout.addWidget(sub)

        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addStretch()

        url = self._guess_url(self._detail)
        if url:
            btn = QtWidgets.QPushButton("\u4f20\u9001\u95e8")
            btn.setObjectName("LinkBtn")
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
            row.addWidget(btn)

        layout.addLayout(row)

if __name__ == "__main__":
    print("Starting Daily Report...")
    import sys
    try:
        app = QtWidgets.QApplication(sys.argv)
        w = SimpleDailyReport()
        w.show()
        print("Widget shown")
        sys.exit(app.exec())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
