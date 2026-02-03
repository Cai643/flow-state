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
    def setData(self, process_data): self.process_data=process_data; self.update()
    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.TextAntialiasing)
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            W, H = self.width(), self.height()
            Y = 20
            total_val = sum(x['value'] for x in self.process_data) or 1
            bar_h = 22
            x0 = 32
            row_h = 38
            font = QtGui.QFont("Microsoft YaHei", 11)
            for i, entry in enumerate(self.process_data):
                pname = truncate_label(entry['name'])
                color = entry.get('color', "#7FAE0F")
                y = Y + i*row_h
                percent = entry['value']/total_val if total_val>0 else 0
                fill_w = int(percent * (W-170))
                # 进程名 label
                p.setFont(font); p.setPen(QtGui.QColor(color))
                p.drawText(12, y+2, 110, 18, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, pname)
                # 进度条背景条
                bg_rect=QtCore.QRect(x0+80, y+2, W-200, bar_h)
                p.setBrush(QtGui.QColor("#F3F7E3")); p.setPen(QtCore.Qt.NoPen)
                p.drawRoundedRect(bg_rect, 10,10)
                # 进度条填充条
                fill_rect=QtCore.QRect(x0+80, y+2, fill_w, bar_h)
                p.setBrush(QtGui.QColor(color)); p.drawRoundedRect(fill_rect, 10,10)
                # 百分比
                p.setPen(QtGui.QColor("#333"))
                p.setFont(QtGui.QFont("Microsoft YaHei",10))
                p.drawText(x0+80+fill_w+6, y+2, 44, bar_h, QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, f"{percent*100:.1f}%")
                hours = round(entry['value']/3600, 1)
                p.drawText(W-54, y+2, 47, bar_h, QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter, f"{hours:.1f}h")
        finally:
            p.end()

class ScreenTimePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMinimumSize(420, 530)
        self.resize(570, 870)
        self._drag_active = False
        self._drag_pos = None

        self.period_mode = "week"  # 默认本周
        self.daily_data, self.process_data, self.total_time, self.module_times = self.load_screen_time_stats(self.period_mode)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(32, 38, 32, 30)
        lay.setSpacing(24)
        titlelay = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("📱  屏幕时间")
        label.setStyleSheet("""
            font-family: "Microsoft YaHei";
            font-size: 24px; font-weight:600;
            color: #5D4037; padding-top:5px;
        """)
        titlelay.addWidget(label)
        titlelay.addStretch()
        self.range_combo = QtWidgets.QComboBox()
        self.range_combo.addItems(["今日","最近7天"])
        self.range_combo.setFixedSize(110, 32)
        self.range_combo.setStyleSheet("""
            QComboBox {font-size:15px;background:rgba(255,255,255,0.72);border-radius:9px;padding:4px 16px;}
            QComboBox::drop-down{border:0;}
            QComboBox::down-arrow {image:none;}
        """)
        self.range_combo.setCurrentIndex(1)
        self.range_combo.currentIndexChanged.connect(self.on_mode_change)
        titlelay.addWidget(self.range_combo)

        close = QtWidgets.QPushButton("×")
        close.setFixedSize(34, 34)
        close.setCursor(QtCore.Qt.PointingHandCursor)
        close.setStyleSheet("""
            QPushButton {
                background: #7FAE0F;  color: #fff; border:none; border-radius:18px; font-size:22px; font-weight:bold;
            }
            QPushButton:hover { background: #558a12; }
        """)
        close.clicked.connect(self.close)
        titlelay.addWidget(close)
        lay.addLayout(titlelay)

        cardrow = QtWidgets.QHBoxLayout()
        cardrow.setSpacing(16)
        cardrow.setContentsMargins(6,18,6,8)

        # --- 这三行才是正确的卡片属性引用！！---
        self.card_total = MiniStatCard("⏱️", "总时间", self.format_time_hm(self.total_time), "#7FAE0F")
        self.card_focus = MiniStatCard("💼", "学习工作", self.format_time_hm(self.module_times.get("学习工作",0)), "#7AA97D")
        self.card_ent = MiniStatCard("🎮", "娱乐", self.format_time_hm(self.module_times.get("娱乐",0)), "#FFC107")
        cardrow.addWidget(self.card_total)
        cardrow.addWidget(self.card_focus)
        cardrow.addWidget(self.card_ent)
        lay.addLayout(cardrow)

        chart_lab = QtWidgets.QLabel("📊 用时分布柱状图")
        chart_lab.setStyleSheet("font-size:16px; font-weight:500; color:#5D4037; margin-top:10px;font-family:'Microsoft YaHei';")
        lay.addWidget(chart_lab)
        self.barchart = BarChart(self.daily_data, mode=self.period_mode)
        lay.addWidget(self.barchart)
        dist_lab = QtWidgets.QLabel("📈 进程排行分布")
        dist_lab.setStyleSheet("font-size:16px; font-weight:500; color:#5D4037;margin-top:10px;font-family:'Microsoft YaHei';")
        lay.addWidget(dist_lab)
        self.catbar = CategoryBar(self.process_data)
        lay.addWidget(self.catbar)
        lay.addStretch()

    def on_mode_change(self, idx):
        mode = "today" if idx == 0 else "week"
        self.period_mode = mode
        daily_data, process_data, total_time, module_times = self.load_screen_time_stats(mode)
        self.set_data(daily_data, process_data, total_time, module_times)
        self.barchart.setData(daily_data, mode=self.period_mode)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self._drag_active and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self._drag_active = False
        super().mouseReleaseEvent(event)

    def set_data(self, daily_data, process_data, total_time, module_times):
        self.daily_data = daily_data
        self.process_data = process_data
        self.total_time = total_time
        self.module_times = module_times

        # --- 卡片内容正确刷新的部分 ---
        self.card_total.value = self.format_time_hm(total_time)
        self.card_focus.value = self.format_time_hm(module_times.get('学习工作',0))
        self.card_ent.value = self.format_time_hm(module_times.get('娱乐',0))
        self.card_total.update()
        self.card_focus.update()
        self.card_ent.update()

        self.barchart.setData(daily_data, mode=self.period_mode)
        self.catbar.setData(process_data)
        self.update()

    @staticmethod
    def format_time_hm(total_sec):
        hours = total_sec / 3600.0
        return f"{hours:.1f}h"

    def load_screen_time_stats(self, mode="week"):
        today = datetime.date.today()
        process_data = []
        module_times = {"学习工作":0, "娱乐":0}
        total_time = 0
        if mode == "today":
            date_str = today.strftime("%Y-%m-%d")
            daily_data = []
            with get_db_connection() as conn:
                # 柱状图和分布条都用进程当天用时 排序
                for row in conn.execute(
                    "SELECT process_name, SUM(duration) as total_sec FROM window_sessions WHERE date(start_time) = ? GROUP BY process_name ORDER BY total_sec DESC", (date_str,)
                ):
                    pname = row['process_name'] or "未知进程"
                    sec = row['total_sec'] or 0
                    hours = round(sec / 3600.0, 1)
                    daily_data.append({'name': pname, 'hours': hours})
                    process_data.append({'name': pname, 'value': sec, 'color': "#9bc284"})
                for row in conn.execute(
                    "SELECT status, SUM(duration) as total_sec FROM window_sessions WHERE date(start_time) = ? GROUP BY status", (date_str,)
                ):
                    state = (row["status"] or "").lower()
                    if state in ["focus", "work"]:
                        module_times["学习工作"] += row["total_sec"] or 0
                    elif state == "entertainment":
                        module_times["娱乐"] += row["total_sec"] or 0
            total_time = sum(module_times.values())
            return daily_data, process_data, total_time, module_times

        # week模式
        days = 7
        date_list = [today - datetime.timedelta(days=days-1-i) for i in range(days)]
        day_labels = ['周一','周二','周三','周四','周五','周六','周日']
        sql_day = """
            SELECT date(start_time) as date, SUM(duration) as total_sec
            FROM window_sessions
            WHERE start_time >= ?
            GROUP BY date(start_time)
            ORDER BY date(start_time)
        """
        days_ago = (today - datetime.timedelta(days=days-1)).strftime("%Y-%m-%d")
        daily_data = []
        with get_db_connection() as conn:
            for i, dt in enumerate(date_list):
                ds = dt.strftime("%Y-%m-%d")
                label = day_labels[dt.weekday()]
                sec = 0
                row = conn.execute("SELECT SUM(duration) as total_sec FROM window_sessions WHERE date(start_time)=?",(ds,)).fetchone()
                if row and row["total_sec"]: sec = row["total_sec"]
                hours = round(sec / 3600.0, 1)
                daily_data.append({'day': label, 'hours': hours})
            for row in conn.execute(
                "SELECT process_name, SUM(duration) as total_sec FROM window_sessions WHERE start_time >= ? GROUP BY process_name ORDER BY total_sec DESC", (days_ago,)
            ):
                pname = row['process_name'] or "未知进程"
                sec = row['total_sec'] or 0
                process_data.append({'name': pname, 'value': sec, 'color': "#9bc284"})
            for row in conn.execute(
                "SELECT status, SUM(duration) as total_sec FROM window_sessions WHERE start_time >= ? GROUP BY status", (days_ago,)
            ):
                state = (row["status"] or "").lower()
                if state in ["focus", "work"]:
                    module_times["学习工作"] += row["total_sec"] or 0
                elif state == "entertainment":
                    module_times["娱乐"] += row["total_sec"] or 0
            total_time = sum(module_times.values())
        return daily_data, process_data, total_time, module_times

    def paintEvent(self, evt):
        p = QtGui.QPainter(self)
        try:
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            rect = self.rect().adjusted(2, 2, -2, -2)
            r = 22
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

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    win = ScreenTimePanel()
    win.show()
    sys.exit(app.exec())