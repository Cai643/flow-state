import datetime
from PySide6 import QtCore, QtGui, QtWidgets
from app.data.core.database import get_db_connection

def truncate_label(label, maxlen=13):
    label = str(label)
    return label if len(label) <= maxlen else label[:maxlen-3] + '...'

class MiniStatCard(QtWidgets.QWidget):
    def __init__(self, icon, label, value, color, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.label = label
        self.value = value
        self.color = QtGui.QColor(color)
        self.bg = QtGui.QColor(color); self.bg.setAlpha(28)
        self.border = QtGui.QColor(color); self.border.setAlpha(66)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.anim = None
        self._scale = 1.0
        self.setMinimumSize(122, 162)
        self.setMaximumSize(220, 230)
    def enterEvent(self, e):
        self.anim_anim(True); super().enterEvent(e)
    def leaveEvent(self, e):
        self.anim_anim(False); super().leaveEvent(e)
    def anim_anim(self, entering):
        if self.anim: self.anim.stop()
        self.anim = QtCore.QPropertyAnimation(self, b"scaleFactor")
        self.anim.setDuration(120)
        self.anim.setEndValue(1.05 if entering else 1.0)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        self.anim.start()
    @QtCore.Property(float)
    def scaleFactor(self): return self._scale
    @scaleFactor.setter
    def scaleFactor(self, v): self._scale = v; self.update()
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            w, h = self.width(), self.height()
            cx, cy = w/2, h/2
            p.translate(cx, cy); p.scale(self._scale, self._scale); p.translate(-cx, -cy)
            r = int(min(w, h) * 0.22)
            p.setPen(QtCore.Qt.NoPen); p.setBrush(self.bg)
            p.drawRoundedRect(6, 6, w-12, h-12, r, r)
            p.setPen(QtGui.QPen(self.border, 1.8)); p.setBrush(QtCore.Qt.NoBrush)
            p.drawRoundedRect(6, 6, w-12, h-12, r, r)
            icon_rect = QtCore.QRect(0, int(h*0.07), w, int(h*0.34))
            font_emoji = QtGui.QFont("Segoe UI Emoji, Microsoft YaHei", int(h*0.32))
            p.setFont(font_emoji); p.setPen(self.color)
            p.drawText(icon_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.icon)
            value_rect = QtCore.QRect(0, int(h*0.50), w, int(h*0.18))
            vfont = QtGui.QFont("Microsoft YaHei", int(h*0.165))
            vfont.setWeight(QtGui.QFont.Bold)
            p.setFont(vfont); p.setPen(QtGui.QColor("#222"))
            p.drawText(value_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.value)
            label_rect = QtCore.QRect(0, int(h*0.79), w, int(h*0.13))
            lfont = QtGui.QFont("Microsoft YaHei", int(h*0.13)); lfont.setWeight(QtGui.QFont.Medium)
            p.setFont(lfont); p.setPen(self.color)
            p.drawText(label_rect, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, self.label)
        finally:
            p.end()

class BarChart(QtWidgets.QWidget):
    """柱状图支持 今日/本周 模式切换 显示平均时间，防0除异常。"""
    def __init__(self, bar_data, mode="week", parent=None):
        super().__init__(parent)
        self.bar_data = bar_data
        self.mode = mode
        self.setMinimumHeight(124)
        self.setMaximumHeight(180)
    def setData(self, bar_data, mode):
        self.bar_data = bar_data
        self.mode = mode
        self.update()
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            W, H = self.width(), self.height()
            bars = self.bar_data or []
            if self.mode == "week":
                bar_w, bar_s = 28, 18
                margin_l, margin_r, margin_t, margin_b = 24, 24, 32, 32
                labels_key = "day"
            else:
                bar_w, bar_s = 28, 18
                margin_l, margin_r, margin_t, margin_b = 24, 24, 38, 32
                labels_key = "name"
            n = len(bars)
            if n == 0:
                return
            bar_area_w = n*bar_w + (n-1)*bar_s
            start_x = (W - bar_area_w) // 2
            max_hours = max((d.get('hours',0) for d in bars), default=0)
            if max_hours == 0:
                max_hours = 1
            avg_hours = sum((d.get('hours',0) for d in bars))/len(bars) if bars else 0

            p.setPen(QtGui.QColor("#7FAE0F66"))
            p.drawLine(margin_l, H-margin_b, W-margin_r, H-margin_b)
            # 右侧显示平均值
            ytext = "AVG:{:.1f}h".format(avg_hours)
            p.setFont(QtGui.QFont("Microsoft YaHei", 11))
            p.setPen(QtGui.QColor("#7FAE0F"))
            p.drawText(W-margin_r-70, margin_t-14, 64, 18, QtCore.Qt.AlignRight, ytext)
            for idx, item in enumerate(bars):
                x = start_x + idx * (bar_w+bar_s)
                h = int((item['hours']/max_hours)*(H-margin_t-margin_b))
                y = H-margin_b-h
                rect = QtCore.QRectF(x, y, bar_w, h)
                grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
                grad.setColorAt(0, QtGui.QColor("#7FAE0F"))
                grad.setColorAt(1, QtGui.QColor("#96C24B"))
                p.setBrush(grad); p.setPen(QtCore.Qt.NoPen)
                p.drawRoundedRect(rect, 7, 7)
                p.setPen(QtGui.QColor("#5d4037"))
                p.setFont(QtGui.QFont("Microsoft YaHei", 8))
                p.drawText(x, y-19, bar_w, 18, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter, f"{item['hours']:.1f}h")
                p.setPen(QtGui.QColor("#888"))
                p.setFont(QtGui.QFont("Microsoft YaHei", 9))
                label_val = item.get(labels_key, "")
                label_val = truncate_label(label_val, 13)
                p.drawText(x, H-margin_b+6, bar_w, 19, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop, label_val)
        finally:
            p.end()

class CategoryBar(QtWidgets.QWidget):
    def __init__(self, process_data, parent=None):
        super().__init__(parent)
        self.process_data = process_data
        self.setMinimumHeight(90)
        self.setMaximumHeight(320)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
    def setData(self, process_data):
        self.process_data = process_data
        rows = max(1, len(self.process_data))
        new_h = rows * 38 + 40
        self.setMinimumHeight(new_h)
        self.setMaximumHeight(new_h)
        self.update()
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.TextAntialiasing)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            W, H = self.width(), self.height()
            Y = 20
            total_val = sum(x['value'] for x in self.process_data) or 1
            bar_h = 22
            x0 = 24
            row_h = 38
            font = QtGui.QFont("Microsoft YaHei", 11)
            name_w = 200
            bar_start_x = x0 + name_w
            base_w = max(80, W - (bar_start_x + 120))
            bar_total_w = min(W - (bar_start_x + 20), int(base_w * 1.5))
            for i, entry in enumerate(self.process_data):
                pname = truncate_label(entry['name'], maxlen=22)
                color = entry.get('color', "#7FAE0F")
                y = Y + i*row_h
                percent = entry['value']/total_val if total_val>0 else 0
                fill_w = int(percent * bar_total_w)
                # 进程名 label
                p.setFont(font); p.setPen(QtGui.QColor(color))
                p.drawText(x0, y+2, name_w, 18, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, pname)
                # 进度条背景条
                bg_rect=QtCore.QRect(bar_start_x, y+2, bar_total_w, bar_h)
                p.setBrush(QtGui.QColor("#F3F7E3")); p.setPen(QtCore.Qt.NoPen)
                p.drawRoundedRect(bg_rect, 10,10)
                # 进度条填充条
                fill_rect=QtCore.QRect(bar_start_x, y+2, fill_w, bar_h)
                p.setBrush(QtGui.QColor(color)); p.drawRoundedRect(fill_rect, 10,10)
                # 百分比
                p.setPen(QtGui.QColor("#333"))
                p.setFont(QtGui.QFont("Microsoft YaHei",10))
                p.drawText(bar_start_x+fill_w+6, y+2, 54, bar_h, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, f"{percent*100:.1f}%")
                hours = round(entry['value']/3600, 1)
                p.drawText(W-64, y+2, 57, bar_h, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, f"{hours:.1f}h")
        finally:
            p.end()

class ScreenTimePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 360)
        self._center_on_screen()

        self.period_mode = "today"

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        hdr = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("今日进程使用信息统计")
        title.setStyleSheet("font-family:'Microsoft YaHei'; font-size:16px; font-weight:600; color:#5D4037;")
        hdr.addWidget(title, 0, QtCore.Qt.AlignLeft)
        hdr.addStretch()
        close_btn = QtWidgets.QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton{color:#5D4037; background:transparent; border:none; font-size:18px; font-weight:bold;} QPushButton:hover{color:#7FAE0F;}")
        close_btn.clicked.connect(self.close)
        hdr.addWidget(close_btn, 0, QtCore.Qt.AlignRight)
        lay.addLayout(hdr)
        # 内容：进程排行分布（可滚动）
        self.process_data = self._load_today_process_data()
        self.catbar = CategoryBar(self.process_data)
        self.catbar.setData(self.process_data)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea{background: transparent;}
            QScrollArea > QWidget {background: transparent;}
            QScrollArea viewport {background: transparent;}
            QScrollBar:vertical {
                background: rgba(127, 174, 15, 40);
                width: 10px;
                margin: 8px 2px 8px 2px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #7FAE0F;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6a9c1f;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; background: transparent; border: none;
            }
            QScrollBar:horizontal {
                background: rgba(127, 174, 15, 40);
                height: 10px;
                margin: 2px 8px 2px 8px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #7FAE0F;
                min-width: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #6a9c1f;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px; background: transparent; border: none;
            }
        """)
        container = QtWidgets.QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QtWidgets.QVBoxLayout(container)
        c_layout.setContentsMargins(0, 6, 0, 6)
        c_layout.addWidget(self.catbar)
        scroll.setWidget(container)
        lay.addWidget(scroll)
        lay.addStretch()

        return

        # （空界面，无内容）

    def on_proc_change(self, idx):
        return

    def mousePressEvent(self, event):
        return
    def mouseMoveEvent(self, event):
        return
    def mouseReleaseEvent(self, event):
        return

    def set_data(self, daily_data, process_data, total_time, module_times):
        return

    @staticmethod
    def format_time_hm(total_sec):
        return "0.0h"

    def load_screen_time_stats(self, mode="week"):
        return [], [], 0, {"学习工作":0, "娱乐":0}

    def _load_today_process_data(self):
        import datetime
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        result = []
        try:
            with get_db_connection() as conn:
                for row in conn.execute(
                    "SELECT process_name, SUM(duration) as total_sec FROM window_sessions WHERE date(start_time) = ? GROUP BY process_name ORDER BY total_sec DESC",
                    (today_str,)
                ):
                    pname = row["process_name"] or "未知进程"
                    sec = int(row["total_sec"] or 0)
                    result.append({"name": pname, "value": sec, "color": "#7FAE0F"})
        except Exception as e:
            print(f"Load today process data failed: {e}")
        return result

    def paintEvent(self, evt):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            rect = self.rect().adjusted(2, 2, -2, -2)
            r = 20
            grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0, QtGui.QColor("#F4F9EC"))
            grad.setColorAt(1, QtGui.QColor("#E0E1AC"))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(rect, r, r)
            p.setPen(QtGui.QPen(QtGui.QColor("#7fae0f"), 1.5))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRoundedRect(rect, r, r)
        finally:
            p.end()

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = ScreenTimePanel()
    sys.exit(0)
