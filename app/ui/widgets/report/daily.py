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
from app.ui.widgets.screen_time_panel import ScreenTimePanel
# from app.data import ActivityHistoryManager

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
        
        # Size
        self.setFixedSize(900, 600)
        
        # Load Data
        self._load_data()
        
        # Build UI
        self._build_ui()
        self._center_on_screen()
        
        # Entry Animation
        self.setWindowOpacity(1.0)
        
        # Auto Refresh Timer
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(50000) # 50 seconds
        self.refresh_timer.timeout.connect(self._refresh_data)
        self.refresh_timer.start()

    def _refresh_data(self):
        """Refresh data and update UI"""
        self._load_data()
        
        # Update Dashboard
        if hasattr(self, 'dashboard_view'):
            self.dashboard_view.update_data()
            
        # Update Timeline
        if hasattr(self, 'timeline_view'):
            self.timeline_view.update_data()

    def _load_data(self):
        """Load data for both dashboard and timeline"""
        self.today = date.today()
        
        # 1. Stats Summary（统一使用每日统计表 daily_stats）
        try:
            from app.data.dao.activity_dao import StatsDAO
            try:
                StatsDAO.recompute_today_from_sessions()
            except Exception:
                pass
            ds = StatsDAO.get_daily_summary(self.today) or {}
            f_time = ds.get('total_focus_time') or ds.get('focus_time') or 0
            total_focus_seconds = f_time
            self.efficiency = ds.get('efficiency_score', 0)
            self.max_streak = ds.get('max_focus_streak', 0)
        except Exception:
            total_focus_seconds = 0
            self.efficiency = 0
            self.max_streak = 0
            
        self.total_focus_minutes = int(total_focus_seconds / 60)
        
        self.daily_goal_minutes = 480 
        if self.daily_goal_minutes > 0:
            self.goal_completion_rate = min(1.0, self.total_focus_minutes / self.daily_goal_minutes)
        else:
            self.goal_completion_rate = 0.0
            
        self.beat_percentage = min(99, int(self.total_focus_minutes / 4.8)) 
        
        hours = self.total_focus_minutes // 60
        minutes = self.total_focus_minutes % 60
        if hours > 0:
            self.duration_text = f"{hours}h {minutes}m"
        else:
            self.duration_text = f"{minutes}m"
            
        self.hours = hours
        self.minutes = minutes
        self.total_focus_mins = self.total_focus_minutes
        
        e_time = int((ds or {}).get("total_entertainment_time") or 0)
        self.recharged_mins = int(e_time / 60)
        
        self.willpower_count = int((ds or {}).get("willpower_wins") or 0)
        self.efficiency_score = self.efficiency

        # 2. Timeline Logs
        self.time_blocks = self._load_timeline_blocks()
        self.peak_flow_mins = 0
        try:
            if self.max_streak:
                 self.peak_flow_mins = int(self.max_streak / 60)
            else:
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
                return []

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

                # Check if we should merge with current block
                should_merge = False
                if current_block and current_block["type"] == s_type:
                    # Check time gap
                    try:
                        last_end_str = current_block.get("end_time_raw")
                        curr_start_str = s.get("start_time")
                        if last_end_str and curr_start_str:
                            fmt = "%Y-%m-%d %H:%M:%S"
                            t1 = datetime.strptime(last_end_str, fmt)
                            t2 = datetime.strptime(curr_start_str, fmt)
                            # If gap is less than 15 minutes, merge
                            if (t2 - t1).total_seconds() < 900: 
                                should_merge = True
                            else:
                                should_merge = False # Explicitly false if gap is large
                    except Exception:
                        # If date parsing fails, fallback to simple type merge
                        should_merge = True

                if should_merge:
                    # Logic: Prevent double counting overlapping duration
                    try:
                        fmt = "%Y-%m-%d %H:%M:%S"
                        last_end_str = current_block.get("end_time_raw")
                        curr_start_str = s.get("start_time")
                        curr_end_str = s.get("end_time")
                        
                        if last_end_str and curr_start_str and curr_end_str:
                            t_last_end = datetime.strptime(last_end_str, fmt)
                            t_curr_start = datetime.strptime(curr_start_str, fmt)
                            t_curr_end = datetime.strptime(curr_end_str, fmt)
                            
                            raw_dur = int(s.get("duration") or 0)
                            
                            # Check overlap
                            if t_curr_start < t_last_end:
                                overlap = (t_last_end - t_curr_start).total_seconds()
                                # Subtract overlap from the new duration to be added
                                # But ensure we don't subtract more than the duration itself (if fully contained)
                                effective_dur = max(0, raw_dur - overlap)
                                current_block["duration_sec"] += effective_dur
                            else:
                                current_block["duration_sec"] += raw_dur
                                
                            # Update end time only if new end is later
                            if t_curr_end > t_last_end:
                                current_block["end_time_raw"] = curr_end_str
                        else:
                             current_block["duration_sec"] += int(s.get("duration") or 0)
                             current_block["end_time_raw"] = s.get("end_time") or current_block.get("end_time_raw")

                    except Exception as e:
                        print(f"Merge error: {e}")
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
            return []

    def _get_mock_blocks(self):
        """Generate mock blocks for visualization when no data exists"""
        return [
            {
                "time_label": "09:00",
                "duration_text": "45m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60", 
                "desc": "09:00",
                "category": "study",
                "duration_sec": 2700,
                "sub_items": [
                    {"window_title": "daily.py - flow_state - Visual Studio Code", "process_name": "code.exe", "summary": "Coding", "duration": 1800, "start_time": "2023-01-01 09:00:00", "end_time": "2023-01-01 09:30:00"},
                    {"window_title": "Stack Overflow - Where is the error?", "process_name": "chrome.exe", "summary": "Research", "duration": 900, "start_time": "2023-01-01 09:30:00", "end_time": "2023-01-01 09:45:00"},
                ]
            },
            {
                "time_label": "09:45",
                "duration_text": "15m",
                "type": "B",
                "title": "\u5145\u7535", 
                "desc": "09:45",
                "category": "break",
                "duration_sec": 900,
                "sub_items": [
                    {"window_title": "Genshin Impact", "process_name": "YuanShen.exe", "summary": "Gaming", "duration": 900, "start_time": "2023-01-01 09:45:00", "end_time": "2023-01-01 10:00:00"}
                ]
            },
            {
                "time_label": "10:00",
                "duration_text": "60m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60",
                "desc": "10:00",
                "category": "study",
                "duration_sec": 3600,
                "sub_items": [
                    {"window_title": "report_widget.py - flow_state", "process_name": "code.exe", "summary": "Coding", "duration": 3600, "start_time": "2023-01-01 10:00:00", "end_time": "2023-01-01 11:00:00"}
                ]
            },
            {
                "time_label": "11:00",
                "duration_text": "10m",
                "type": "B",
                "title": "\u5145\u7535",
                "desc": "11:00",
                "category": "short_video",
                "duration_sec": 600,
                "sub_items": [
                    {"window_title": "\u6296\u97f3 - \u8bb0\u5f55\u7f8e\u597d\u751f\u6d3b", "process_name": "chrome.exe", "summary": "Douyin", "duration": 600, "start_time": "2023-01-01 11:00:00", "end_time": "2023-01-01 11:10:00"}
                ]
            },
            {
                "time_label": "11:10",
                "duration_text": "30m",
                "type": "A",
                "title": "\u5de5\u4f5c\u5b66\u4e60",
                "desc": "11:10",
                "category": "web_other",
                "duration_sec": 1800,
                "sub_items": [
                    {"window_title": "GitHub - flow_state/issues", "process_name": "chrome.exe", "summary": "GitHub", "duration": 1800, "start_time": "2023-01-01 11:10:00", "end_time": "2023-01-01 11:40:00"}
                ]
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
            
        # Add summary text for visualization
        # "探索霸王龙..." or "大脑呼吸中"
        if block.get("type") == "B":
            block["summary_text"] = "\u5927\u8111\u547c\u5438\u4e2d" # "Brain Breathing"
        else:
            # Find most common title or summary
            details = []
            for s in block.get("sub_items") or []:
                t = s.get("summary") or s.get("window_title") or ""
                if t: details.append(t)
            
            if details:
                # Simple pick first or longest? Let's pick first valid
                txt = details[0]
                if len(txt) > 6:
                    txt = txt[:6] + "..."
                block["summary_text"] = txt
            else:
                block["summary_text"] = "\u4e13\u6ce8\u65f6\u523b" # "Focus Time"

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
            }
        """)
        main_layout.addWidget(self.container)
        
        # Overlay Border (to ensure it stays on top of scroll content)
        self.border_overlay = QtWidgets.QLabel(self)
        self.border_overlay.setStyleSheet("""
            background: transparent;
            border: 2px solid #66BB6A;
            border-radius: 20px;
        """)
        self.border_overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.border_overlay.raise_()
        
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

    def resizeEvent(self, event):
        if hasattr(self, 'border_overlay'):
            self.border_overlay.resize(self.size())
        super().resizeEvent(event)

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

    def update_data(self):
        """Rebuild timeline with new data"""
        # Remove old container
        if hasattr(self, 'timeline_container'):
            self.timeline_container.deleteLater()
            
        # Create new one
        self.timeline_container = TimelineContainer(self.report.time_blocks)
        
        # Set to scroll area
        # Need to find scroll area from layout
        scroll = self.layout().itemAt(1).widget()
        if isinstance(scroll, QtWidgets.QScrollArea):
            scroll.setWidget(self.timeline_container)

    def _build_header(self, parent_layout):
        header = QtWidgets.QWidget()
        header.setFixedHeight(70) 
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 0)
        
        # Back
        btn_back = QtWidgets.QPushButton("< \u8fd4\u56de") # "< "
        btn_back.setCursor(QtCore.Qt.PointingHandCursor)
        btn_back.setStyleSheet("color: #50795D; font-weight: bold; border: none; font-size: 16px;") 
        btn_back.clicked.connect(self.close_req.emit)
        
        # Date
        lbl_date = QtWidgets.QLabel(date.today().strftime("%Y.%m.%d %A"))
        lbl_date.setStyleSheet("color: #2E4E3F; font-size: 20px; font-weight: bold;") 
        lbl_date.setAlignment(QtCore.Qt.AlignCenter)
        
        # Switch
        btn_switch = QtWidgets.QPushButton("\u5207\u6362\u5230\u65f6\u95f4\u8f74 >") 
        btn_switch.setCursor(QtCore.Qt.PointingHandCursor)
        btn_switch.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2E7D32;
                border: none;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #1B5E20;
            }
        """)
        btn_switch.clicked.connect(self.switch_to_timeline.emit)
        # ======= 排列顺序调整 =======
        h_layout.addWidget(btn_back)
        h_layout.addStretch()
        h_layout.addWidget(lbl_date)
        h_layout.addStretch()
        h_layout.addWidget(btn_switch)       # “切换到时间轴”按钮在右
        
        parent_layout.addWidget(header)

        # 保存面板实例，防止多窗口
        self._screen_time_panel = None

    def open_screen_time_panel(self):
        if self._screen_time_panel is None or not self._screen_time_panel.isVisible():
            self._screen_time_panel = ScreenTimePanel()
        self._screen_time_panel.show()
        self._screen_time_panel.raise_()
        
    def _build_left_panel(self, parent_layout):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet("""
            QWidget {
                background-color: #E8F5E9;
                border-radius: 20px;
            }
        """)
        v_layout = QtWidgets.QVBoxLayout(panel)
        v_layout.setContentsMargins(25, 25, 25, 25)
        
        top_row = QtWidgets.QHBoxLayout()
        t1 = QtWidgets.QLabel("\ud83c\udfaf \u4eca\u65e5\u76ee\u6807\u8fdb\u5ea6") 
        t1.setStyleSheet("color: #2E7D32; font-weight: bold; font-size: 16px; background: transparent;")
        
        goal_percent_text = f"{int(self.report.goal_completion_rate * 100)}%"
        self.lbl_goal_percent = QtWidgets.QLabel(goal_percent_text)
        self.lbl_goal_percent.setStyleSheet("color: #2E7D32; font-weight: bold; font-size: 20px; background: transparent;")
        top_row.addWidget(t1)
        top_row.addStretch()
        top_row.addWidget(self.lbl_goal_percent)
        v_layout.addLayout(top_row)
        
        v_layout.addStretch()
        
        self.ring = ProgressRingWidget(percentage=self.report.goal_completion_rate, center_text=f"{self.report.hours}\u5c0f\u65f6{self.report.minutes}\u5206", sub_text="\u4eca\u65e5\u4e13\u6ce8") 
        v_layout.addWidget(self.ring, 0, QtCore.Qt.AlignCenter)
        
        v_layout.addStretch()
        
        self.lbl_beat = QtWidgets.QLabel(f"\ud83c\udfc6 \u51fb\u8d25\u5168\u56fd {self.report.beat_percentage}% \u7684\u7528\u6237") 
        self.lbl_beat.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_beat.setStyleSheet("color: #1B5E20; font-size: 15px; font-weight: bold; background: transparent;")
        
        f2 = QtWidgets.QLabel("\u72b6\u6001: \ud83d\udfe2 \u6df1\u5ea6\u6c89\u6d78\u4e2d...") 
        f2.setAlignment(QtCore.Qt.AlignCenter)
        f2.setStyleSheet("color: #2E7D32; font-size: 14px; font-weight: bold; background: #C8E6C9; border-radius: 12px; padding: 6px 12px; margin-top: 10px;")
        
        v_layout.addWidget(self.lbl_beat)
        v_layout.addWidget(f2)
        
        parent_layout.addWidget(panel, 1)

    def _build_right_panel(self, parent_layout):
        right_container = QtWidgets.QWidget()
        v_layout = QtWidgets.QVBoxLayout(right_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(20)
        
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(20)
        
        self.c1 = StatCard("\u5dc5\u5cf0\u5fc3\u6d41", f"{self.report.peak_flow_mins}", "\u5206\u949f", "\u26a1", "#F0F4C3", "#827717")
        self.c2 = StatCard("\u610f\u5fd7\u529b", f"{self.report.willpower_count}", "\u6b21\u6210\u529f", "\ud83d\udee1\ufe0f", "#FFECB3", "#FF6F00")
        self.c3 = StatCard("\u5df2\u5145\u80fd", f"{self.report.recharged_mins}", "\u5206\u949f", "\ud83d\udd0b", "#DCEDC8", "#33691E")
        self.c4 = StatCard("\u6548\u80fd\u6307\u6570", f"{self.report.efficiency_score}", "\u5206", "\ud83d\udcc8", "#FFCCBC", "#BF360C")
        
        for c in [self.c1, self.c2, self.c3, self.c4]:
            c.setMinimumHeight(125)
        
        grid.addWidget(self.c1, 0, 0)
        grid.addWidget(self.c2, 0, 1)
        grid.addWidget(self.c3, 1, 0)
        grid.addWidget(self.c4, 1, 1)
        
        v_layout.addLayout(grid, 3)
        
        comm_box = QtWidgets.QWidget()
        comm_box.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            border: 2px solid #C8E6C9;
        """)
        comm_box.setFixedHeight(130) # Changed from setMaximumHeight to setFixedHeight to force size
        
        comm_layout = QtWidgets.QVBoxLayout(comm_box)
        comm_layout.setContentsMargins(20, 15, 20, 15) 
        
        title = QtWidgets.QLabel("\ud83d\udca1 \u6bcf\u65e5\u91d1\u53e5") # Daily Golden Quote
        title.setStyleSheet("color: #455A64; font-weight: 900; font-size: 16px; border: none;") # Increased font size from 14 to 16
        
        import random
        quotes = [
            "\u4e13\u6ce8\u662f\u7075\u9b42\u7684\u547c\u5438\uff0c\u5728\u6bcf\u4e00\u6b21\u6df1\u547c\u5438\u4e2d\uff0c\u4f60\u4e0e\u66f4\u597d\u7684\u81ea\u5df1\u76f8\u9047\u3002",
            "\u6d41\u6c34\u4e0d\u4e89\u5148\uff0c\u4e89\u7684\u662f\u6ed4\u6ed4\u4e0d\u7edd\u3002\u6301\u7eed\u7684\u4e13\u6ce8\u80dc\u8fc7\u77b3\u95f4\u7684\u7206\u53d1\u3002",
            "\u5fc3\u6d41\u72b6\u6001\u4e0b\uff0c\u65f6\u95f4\u4e0d\u662f\u6d41\u901d\u7684\uff0c\u800c\u662f\u4e3a\u4f60\u505c\u7559\u7684\u3002",
            "\u5728\u55a7\u56a3\u7684\u4e16\u754c\u91cc\uff0c\u4e13\u6ce8\u529b\u662f\u4f60\u6700\u5b9d\u8d35\u7684\u8d44\u4ea7\u3002",
            "\u6548\u7387\u4e0d\u662f\u505a\u5f97\u66f4\u5feb\uff0c\u800c\u662f\u628a\u751f\u547d\u7684\u5149\u7167\u8fdb\u6700\u91cd\u8981\u7684\u4e8b\u60c5\u91cc\u3002",
            "\u6700\u597d\u7684\u4f11\u606f\u4e0d\u662f\u505c\u6b62\u601d\u8003\uff0c\u800c\u662f\u8ba9\u5927\u8111\u5728\u4e13\u6ce8\u4e0e\u653e\u677e\u95f4\u81ea\u7531\u5207\u6362\u3002",
            "\u4f60\u628a\u65f6\u95f4\u82b1\u5728\u54ea\u91cc\uff0c\u4f60\u7684\u6210\u5c31\u5c31\u5728\u54ea\u91cc\u3002",
            "\u4e0d\u8981\u7b49\u5f85\u7075\u611f\uff0c\u4e13\u6ce8\u672c\u8eab\u5c31\u662f\u5524\u9192\u7075\u611f\u7684\u4eea\u5f0f\u3002",
            "\u79cd\u4e00\u68f5\u6811\u6700\u597d\u7684\u65f6\u95f4\u662f\u5341\u5e74\u524d\uff0c\u517c\u6b21\u662f\u73b0\u5728\u3002\u4e13\u6ce8\u4ea6\u7136\u3002",
            "\u5b81\u9759\u81f4\u8fdc\uff0c\u4e13\u6ce8\u81f4\u6df1\u3002"
        ]
        selected_quote = random.choice(quotes)
        
        msg = QtWidgets.QLabel(f'"{selected_quote}"')
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #37474F; font-size: 15px; font-weight: bold; margin-top: 8px; border: none; line-height: 1.5;") # Increased font size from 13 to 15, margin-top from 5 to 8, line-height from 1.4 to 1.5 
        
        comm_layout.addWidget(title)
        comm_layout.addWidget(msg)
        comm_layout.addStretch()
        
        v_layout.addWidget(comm_box, 1)

        # Bottom Buttons (History & Screen Time)
        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.setAlignment(QtCore.Qt.AlignCenter)
        btns_layout.setSpacing(100) # Increased spacing to push buttons apart
        
        # History Button
        btn_history = QtWidgets.QPushButton("历史回溯")
        btn_history.setCursor(QtCore.Qt.PointingHandCursor)
        btn_history.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2E7D32;
                border: none;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #1B5E20;
            }
        """)
        btn_history.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://localhost:8080")))
        
        # Screen Time Button
        btn_screen_time = QtWidgets.QPushButton("今日进程统计")
        btn_screen_time.setCursor(QtCore.Qt.PointingHandCursor)
        btn_screen_time.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2E7D32;
                border: none;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #1B5E20;
            }
        """)
        btn_screen_time.clicked.connect(self.open_screen_time_panel)
        
        btns_layout.addWidget(btn_history)
        btns_layout.addWidget(btn_screen_time)
        
        v_layout.addLayout(btns_layout)
        
        parent_layout.addWidget(right_container, 1)

    def update_data(self):
        """Update UI with new data from report"""
        # Update Goal Percent
        self.lbl_goal_percent.setText(f"{int(self.report.goal_completion_rate * 100)}%")
        
        # Update Ring
        self.ring.percentage = self.report.goal_completion_rate
        self.ring.center_text = f"{self.report.hours}\u5c0f\u65f6{self.report.minutes}\u5206"
        self.ring.update()
        
        # Update Beat Percent
        self.lbl_beat.setText(f"\ud83c\udfc6 \u51fb\u8d25\u5168\u56fd {self.report.beat_percentage}% \u7684\u7528\u6237")
        
        # Update Cards
        self.c1.update_value(f"{self.report.peak_flow_mins}")
        self.c2.update_value(f"{self.report.willpower_count}")
        self.c3.update_value(f"{self.report.recharged_mins}")
        self.c4.update_value(f"{self.report.efficiency_score}")


class ProgressRingWidget(QtWidgets.QWidget):
    def __init__(self, percentage=0.45, center_text="", sub_text=""):
        super().__init__()
        self.percentage = percentage
        self.center_text = center_text
        self.sub_text = sub_text
        self.setFixedSize(280, 280)
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect().adjusted(20, 20, -20, -20)
        
        pen = QtGui.QPen(QtGui.QColor("#C8E6C9"), 24) 
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        
        pen.setColor(QtGui.QColor("#43A047"))
        painter.setPen(pen)
        span_angle = int(-self.percentage * 360 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)
        
        painter.setPen(QtCore.Qt.NoPen)
        
        # Draw Tree (Top Center)
        font = QtGui.QFont()
        font.setPixelSize(80) 
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#2E7D32"))
        # Position: Center X, Top Y roughly 1/4 down
        painter.drawText(QtCore.QRectF(0, 50, self.width(), 80), QtCore.Qt.AlignCenter, "\ud83c\udf33") 
        
        # Draw Center Text (Time) - Middle
        font.setPixelSize(40) 
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#1B5E20"))
        # Position: Center X, Middle Y
        painter.drawText(QtCore.QRectF(0, 135, self.width(), 50), QtCore.Qt.AlignCenter, self.center_text)
        
        # Draw Sub Text (Label) - Bottom
        font.setPixelSize(16) 
        font.setBold(True) 
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#388E3C"))
        # Position: Center X, Below Time
        painter.drawText(QtCore.QRectF(0, 180, self.width(), 30), QtCore.Qt.AlignCenter, self.sub_text)


class StatCard(QtWidgets.QFrame):
    def __init__(self, title, value, unit, icon, bg_color, text_color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 20px;
            }}
        """)
        
        # Main Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)
        
        # 1. Top Left: Small Icon + Title
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        
        # Small Icon
        lbl_small_icon = QtWidgets.QLabel(icon)
        lbl_small_icon.setStyleSheet(f"background: transparent; font-size: 18px; color: {text_color};")
        lbl_small_icon.setAlignment(QtCore.Qt.AlignCenter)
        
        # Title
        l_title = QtWidgets.QLabel(title + ":")
        l_title.setStyleSheet(f"color: {text_color}; font-size: 15px; font-weight: bold; background: transparent; opacity: 0.9;")
        
        top_row.addWidget(lbl_small_icon)
        top_row.addWidget(l_title)
        top_row.addStretch()
        
        layout.addLayout(top_row)
        
        # 2. Center: Large Value + Unit
        # Use a centered layout that takes up the remaining space
        self._center_layout = QtWidgets.QHBoxLayout()
        self._center_layout.setAlignment(QtCore.Qt.AlignCenter)
        self._center_layout.setSpacing(6)
        
        self._value_label = QtWidgets.QLabel(str(value))
        # Significantly larger font
        self._value_label.setStyleSheet(f"color: {text_color}; font-size: 52px; font-weight: 900; background: transparent;")
        
        l_unit = QtWidgets.QLabel(unit)
        l_unit.setStyleSheet(f"color: {text_color}; font-size: 16px; font-weight: bold; padding-top: 24px; background: transparent; opacity: 0.85;")
        
        self._center_layout.addWidget(self._value_label)
        self._center_layout.addWidget(l_unit)
        
        layout.addStretch()
        layout.addLayout(self._center_layout)
        layout.addStretch()



    def update_value(self, value):
        try:
            if isinstance(self._value_label, QtWidgets.QLabel):
                self._value_label.setText(str(value))
        except Exception as e:
            print(f"Error updating stat card: {e}")

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
        
        # Header
        self._build_header(layout)
        
        # Scroll Area
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("background: transparent; border: none;")
        self._scroll.viewport().setStyleSheet("background: transparent;")
        
        # Styled scrollbar
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:horizontal {
                border: none;
                background: rgba(255,255,255,100);
                height: 18px;
                margin: 0px 26px 10px 26px;
                border-radius: 9px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(90, 140, 115, 200);
                min-width: 40px;
                border-radius: 9px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
        """)
        
        # Timeline Container
        self.timeline_container = TimelineContainer(self.report.time_blocks)
        self._scroll.setWidget(self.timeline_container)
        
        layout.addWidget(self._scroll)

    def wheelEvent(self, event):
        """Handle mouse wheel to scroll horizontally"""
        if event.angleDelta().y() != 0:
            # Convert vertical scroll (wheel) to horizontal scroll
            h_bar = self._scroll.horizontalScrollBar()
            # Scroll speed factor
            step = event.angleDelta().y()
            h_bar.setValue(h_bar.value() - step)
            event.accept()
        else:
            super().wheelEvent(event)

    def update_data(self):
        try:
            self.timeline_container.deleteLater()
        except Exception:
            pass
        self.timeline_container = TimelineContainer(self.report.time_blocks)
        if hasattr(self, '_scroll'):
            self._scroll.setWidget(self.timeline_container)

    def _build_header(self, parent_layout):
        header = QtWidgets.QWidget()
        header.setFixedHeight(70)
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        btn_back = QtWidgets.QPushButton("< \u8fd4\u56de") 
        btn_back.setCursor(QtCore.Qt.PointingHandCursor)
        btn_back.setStyleSheet("color: #50795D; font-weight: bold; border: none; font-size: 16px;")
        btn_back.clicked.connect(self.close_req.emit)
        
        lbl_date = QtWidgets.QLabel(date.today().strftime("%Y.%m.%d %A"))
        lbl_date.setStyleSheet("color: #2E4E3F; font-size: 20px; font-weight: bold;")
        lbl_date.setAlignment(QtCore.Qt.AlignCenter)
        
        btn_summary = QtWidgets.QPushButton("< \u56de\u5230\u4eca\u65e5\u603b\u7ed3") 
        btn_summary.setCursor(QtCore.Qt.PointingHandCursor)
        btn_summary.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2E7D32;
                border: none;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                color: #1B5E20;
            }
        """)
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
        self._padding_x = 80
        self._slot_w = 220
        self._y_center = 220 
        self._card_w = 160   
        self._card_h = 90   
        self._node_size = 24
        self._gap_node_to_card = 20

        self._items = []
        for i, block in enumerate(self.blocks):
            # Alternating layout: Even -> Top, Odd -> Bottom
            is_top = (i % 2 == 0)
            item = TimelineItemWidget(self, block, is_top)
            self._items.append(item)

        total_w = self._padding_x * 2 + max(1, len(self._items)) * self._slot_w
        self.setFixedSize(total_w, 440) 
        self._layout_items()

    def _layout_items(self):
        for idx, item in enumerate(self._items):
            slot_x = self._padding_x + idx * self._slot_w
            node_x = int(slot_x + (self._slot_w / 2) - (self._node_size / 2))
            node_y = int(self._y_center - (self._node_size / 2))
            card_x = int(slot_x + (self._slot_w / 2) - (self._card_w / 2))
            
            if item.is_top:
                # Card Above Line
                card_y = int(node_y - self._gap_node_to_card - self._card_h)
                desc_y = int(node_y + self._node_size + 10) # Text below line
            else:
                # Card Below Line
                card_y = int(node_y + self._node_size + self._gap_node_to_card)
                desc_y = int(node_y - 30) # Text above line
            
            # Use geometry to contain everything, but place() does the internal layout
            item.setGeometry(card_x, 0, self._card_w, self.height())
            item.place(card_x, card_y, node_x, node_y, desc_y, self._card_w, self._card_h, self._node_size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        y_center = self._y_center

        # Glow Effect
        glow = QtGui.QPen(QtGui.QColor(165, 214, 167, 100), 12) # Light Green Glow
        glow.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(glow)
        painter.drawLine(0, y_center, self.width(), y_center)

        # Core Line
        main = QtGui.QPen(QtGui.QColor(129, 199, 132, 220), 4) # Solid Green
        main.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(main)
        painter.drawLine(0, y_center, self.width(), y_center)
        
        # Connectors for items
        for item in self._items:
            center = item.node_center()
            if not center: continue
            
            # Draw small connector from node to card if needed? 
            # The node sits on the line. The card floats.
            # Wireframe shows a small triangle/tip on the card pointing to the node.
            # So no extra line needed here.
            pass


class BubbleCard(QtWidgets.QWidget):
    clicked = Signal(object)
    hoverChanged = Signal(bool)

    def __init__(self, data, is_top):
        super().__init__()
        self.data = data
        self.is_top = is_top
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        
        # Color Palette based on Type
        # Type A (Focus) -> Sage Green
        # Type B (Break) -> Creamy Beige
        
        if data.get("type") == "B":
             # Break: Cream Background, Warm Text
             self.bg_color = QtGui.QColor("#FFF9C4") # Light Yellow/Cream
             self.text_color = QtGui.QColor("#5D4037") # Brownish
             self.icon_color = QtGui.QColor("#FBC02D") # Mustard
             self.border_color = QtGui.QColor(251, 192, 45, 100)
             self.icon_char = "\u2615" # Coffee
        else:
             # Work: Green Background, Green Text
             self.bg_color = QtGui.QColor("#DCEDC8") # Light Sage
             self.text_color = QtGui.QColor("#1B5E20") # Dark Green
             self.icon_color = QtGui.QColor("#33691E") # Darker Green
             self.border_color = QtGui.QColor(51, 105, 30, 100)
             self.icon_char = "\ud83c\udf33" # Tree

        self._shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(15)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QtGui.QColor(0, 0, 0, 30))
        self.setGraphicsEffect(self._shadow)
        self._hovered = False

    def tip_apex_y(self):
        # Return local Y coordinate of the tip
        if self.is_top:
            return self.height() 
        else:
            return 0

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.data)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect_h = self.height() - 12 # Reserve space for tip
        tip_h = 12
        
        path = QtGui.QPainterPath()
        
        if self.is_top:
            # Card is above, tip points down
            rect = QtCore.QRectF(0, 0, self.width(), rect_h)
            tip_y = rect_h
            tip_x = self.width() / 2
            
            path.addRoundedRect(rect, 16, 16)
            path.moveTo(tip_x - 8, tip_y)
            path.lineTo(tip_x, tip_y + tip_h)
            path.lineTo(tip_x + 8, tip_y)
            path.closeSubpath()
        else:
            # Card is below, tip points up
            rect = QtCore.QRectF(0, tip_h, self.width(), rect_h)
            tip_y = tip_h
            tip_x = self.width() / 2
            
            path.addRoundedRect(rect, 16, 16)
            path.moveTo(tip_x - 8, tip_y)
            path.lineTo(tip_x, tip_y - tip_h)
            path.lineTo(tip_x + 8, tip_y)
            path.closeSubpath()

        # Draw
        if self._hovered:
            painter.setBrush(self.bg_color.lighter(105))
        else:
            painter.setBrush(self.bg_color)
            
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPath(path)
        
        # Content
        # Icon
        y_off = 0 if self.is_top else tip_h
        icon_rect = QtCore.QRectF(15, 15 + y_off, 40, 40)
        font = QtGui.QFont()
        font.setPixelSize(32)
        painter.setFont(font)
        painter.setPen(self.icon_color)
        painter.drawText(icon_rect, QtCore.Qt.AlignCenter, self.icon_char)
        
        # Title (Work/Rest)
        title_rect = QtCore.QRectF(65, 15 + y_off, self.width() - 70, 20)
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self.text_color)
        title_txt = "\u5de5\u4f5c\u5b66\u4e60" if self.data.get("type") == "A" else "\u5145\u7535"
        painter.drawText(title_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, title_txt)
        
        # Duration
        dur_rect = QtCore.QRectF(65, 35 + y_off, self.width() - 70, 30)
        font.setPixelSize(24)
        font.setBold(True)
        font.setWeight(QtGui.QFont.Black)
        painter.setFont(font)
        painter.drawText(dur_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.data.get("duration_text", ""))

class TimelineItemWidget(QtWidgets.QWidget):
    def __init__(self, parent, block_data, is_top):
        super().__init__(parent)
        self.block_data = block_data
        self.is_top = is_top
        
        self._card = BubbleCard(block_data, is_top)
        
        # Start Time (e.g. "09:00")
        self._desc = QtWidgets.QLabel(block_data.get("desc", ""))
        self._desc.setAlignment(QtCore.Qt.AlignCenter)
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: #1B5E20; font-size: 13px; font-weight: bold; background: transparent;")

        # Node (Solid Green or Hollow Yellow)
        is_rest = (block_data.get("type") == "B")
        self._node = TimelineNode(is_rest)

        self._card.setParent(self)
        self._desc.setParent(self)
        self._node.setParent(self)
        
        # Make visible again!
        self._node.show()
        self._card.show()
        self._desc.show()

        self._node_pos = None
        self._card.clicked.connect(self._show_details)
        self._popup = None

    def place(self, card_x, card_y, node_x, node_y, desc_y, card_w, card_h, node_size):
        # Card
        self._card.setFixedSize(card_w, card_h + 12) # +tip
        self._card.move(0, card_y)
        
        # Node
        self._node.setFixedSize(node_size, node_size)
        self._node.move(node_x - self.x(), node_y)
        
        # Text
        self._desc.setFixedWidth(card_w + 40) # Allow wider text
        self._desc.move(int((card_w - self._desc.width()) / 2), desc_y)

        self._node_pos = (node_x + int(node_size / 2), node_y + int(node_size / 2))
        self.update()

    def node_center(self):
        return self._node_pos

    def _show_details(self, data: dict):
        try:
            if self._popup and self._popup.isVisible():
                self._popup.close()
        except RuntimeError:
            self._popup = None

        self._popup = TimelineDetailPopup(None, data)
        self._popup.adjustSize()
        
        # Center popup on screen
        screen = QtGui.QGuiApplication.primaryScreen()
        geo = screen.geometry()
        x = (geo.width() - self._popup.width()) // 2
        y = (geo.height() - self._popup.height()) // 2
        self._popup.move(x, y)
        self._popup.show()

class TimelineNode(QtWidgets.QWidget):
    def __init__(self, is_rest):
        super().__init__()
        self.is_rest = is_rest
        self.setFixedSize(24, 24)
        self._hovered = False

    def set_hover(self, hovered: bool):
        if self._hovered != hovered:
            self._hovered = hovered
            self.update()
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        if self.is_rest:
            # Hollow Yellow Node
            # Fill: White/Cream
            painter.setBrush(QtGui.QColor("#FFF9C4"))
            # Border: Yellow/Orange
            pen = QtGui.QPen(QtGui.QColor("#FBC02D"), 3)
            painter.setPen(pen)
            painter.drawEllipse(rect)
        else:
            # Solid Green Node
            # Fill: Green
            painter.setBrush(QtGui.QColor("#66BB6A"))
            # Border: White ring? Or just solid
            pen = QtGui.QPen(QtGui.QColor("#FFFFFF"), 2) # White border to pop from line
            painter.setPen(pen)
            painter.drawEllipse(rect)


class TimelineDetailPopup(QtWidgets.QDialog):
    def __init__(self, parent, block_data: dict):
        super().__init__(None)
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        
        self._block_data = block_data or {}
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
        # Simplified regex to avoid re.error (multiple repeat) and cover most cases
        m = re.search(r"(https?://\S+)", text)
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
        accent_rgb = f"{accent.red()}, {accent.green()}, {accent.blue()}"
        
        # 1. Main Window Layout (with margins for shadow)
        self.setStyleSheet("background: transparent;")
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 2. Content Frame
        self.content_frame = QtWidgets.QFrame()
        self.content_frame.setObjectName("PopupContent")
        self.content_frame.setStyleSheet(f"""
            QFrame#PopupContent {{
                background: #FFF9E6; 
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
        
        # Shadow on Content Frame
        self._shadow = QtWidgets.QGraphicsDropShadowEffect(self.content_frame)
        self._shadow.setBlurRadius(26)
        self._shadow.setOffset(0, 10)
        self._shadow.setColor(QtGui.QColor(0, 0, 0, 60))
        self.content_frame.setGraphicsEffect(self._shadow)
        
        main_layout.addWidget(self.content_frame)
        
        # Limit width (including margins)
        self.setMinimumWidth(400) # 360 + 40
        self.setMaximumWidth(460) # 420 + 40

        layout = QtWidgets.QVBoxLayout(self.content_frame)
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
        
        # Styled Vertical Scrollbar (Matching Timeline Style)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0);
                width: 10px;
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(90, 140, 115, 200);
                min-height: 40px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        scroll.viewport().setStyleSheet("background: transparent;")

        body = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(body)
        v.setContentsMargins(0, 0, 10, 0) # Add right margin to separate content from scrollbar
        v.setSpacing(8)

        for d in details:
            v.addWidget(TimelineDetailRow(d, accent, self._fmt_hm, self._guess_url))
        v.addStretch()

        scroll.setWidget(body)
        scroll.setFixedHeight(min(260, max(120, 28 + len(details) * 54)))
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
        self.setObjectName("DetailRow")
        self.setStyleSheet(f"""
            QFrame#DetailRow {{
                background: rgba(255, 255, 255, 255);
                border: 1px solid rgba({self._accent.red()}, {self._accent.green()}, {self._accent.blue()}, 255);
                border-radius: 14px;
            }}
            QLabel {{
                border: none;
                background: transparent;
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
