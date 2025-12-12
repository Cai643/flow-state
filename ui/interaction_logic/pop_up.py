try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal

class ImageOverlay(QtWidgets.QWidget):
    """
    全屏显示图片的覆盖层。
    点击任意位置关闭。
    """
    closed = Signal()

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        # 无边框 | 工具窗口 | 始终置顶
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        )
        # 背景半透明黑色
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.bg_color = QtGui.QColor(0, 0, 0, 150) # 半透明遮罩

        self.image_path = image_path
        self.pixmap = QtGui.QPixmap(image_path)
        
        # 初始化时调整到屏幕大小
        self.updateGeometryToScreen()

    def updateGeometryToScreen(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 1. 绘制半透明背景遮罩
        p.fillRect(self.rect(), self.bg_color)
        
        # 2. 绘制居中图片
        if not self.pixmap.isNull():
            # 计算居中位置
            img_w = self.pixmap.width()
            img_h = self.pixmap.height()
            
            # 如果图片比屏幕大，按比例缩放
            screen_size = self.size()
            if img_w > screen_size.width() or img_h > screen_size.height():
                self.pixmap = self.pixmap.scaled(
                    screen_size * 0.9, 
                    QtCore.Qt.KeepAspectRatio, 
                    QtCore.Qt.SmoothTransformation
                )
                img_w = self.pixmap.width()
                img_h = self.pixmap.height()
            
            x = (self.width() - img_w) / 2
            y = (self.height() - img_h) / 2
            p.drawPixmap(int(x), int(y), self.pixmap)

    def mousePressEvent(self, event):
        # 点击任意位置关闭
        self.close()
        self.closed.emit()


class SearchFrame(QtWidgets.QWidget):
    """
    胶囊状的搜索框组件。
    """
    clicked = Signal()
    daily_clicked = Signal()
    weekly_clicked = Signal()
    monthly_clicked = Signal()

    def __init__(self, parent=None, text="Cai,是否查询历史报告？", bg_color="#2b2b2b", text_color="#DDDDDD"):
        super().__init__(parent)
        self.default_text = text
        self.hover_text = "每月报告  |  每周报告  |  每日报告"
        self.text = self.default_text
        self.bg_color = QtGui.QColor(bg_color)
        self.text_color = QtGui.QColor(text_color)
        self.font = QtGui.QFont("Microsoft YaHei", 12)
        self.setCursor(QtCore.Qt.PointingHandCursor) # 设置手型光标
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.text = self.hover_text
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.text = self.default_text
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 绘制胶囊状背景
        rect = self.rect()
        radius = rect.height() / 2
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), radius, radius)
        p.fillPath(path, self.bg_color)
        
        # 绘制文字（居中对齐）
        p.setPen(self.text_color)
        p.setFont(self.font)
        p.drawText(rect, QtCore.Qt.AlignCenter, self.text)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.text == self.hover_text:
                # Determine which section was clicked
                # "每月报告  |  每周报告  |  每日报告"
                w = self.width()
                x = event.pos().x()
                if x < w / 3:
                    self.monthly_clicked.emit()
                elif x < 2 * w / 3:
                    self.weekly_clicked.emit()
                else:
                    self.daily_clicked.emit()
            else:
                self.clicked.emit() # 发送点击信号
            event.accept()


class CardPopup(QtWidgets.QWidget):
    """
    包含图表和搜索框的弹出窗口。
    负责管理布局、定位和动画效果。
    """
    request_full_report = Signal()

    def __init__(self, image_path, target_margin=(5, 7), ball_size=64):
        super().__init__()
        # 设置窗口标志：无边框 | 工具窗口（不在任务栏显示） | 始终置顶
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        )
        # 设置背景透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.target_margin = target_margin
        self.ball_size = ball_size
        
        # 图片标签
        self.label = QtWidgets.QLabel(self)
        self.label.setScaledContents(True)
        self.pix = QtGui.QPixmap(image_path)
        self.label.setPixmap(self.pix)
        self.orig_pix_size = self.pix.size()
        
        # 搜索框组件
        self.search_frame = SearchFrame(self)
        self.search_frame.clicked.connect(self.request_full_report.emit) # 连接信号
        self.search_frame.daily_clicked.connect(self.show_daily_report)
        self.search_frame.weekly_clicked.connect(self.show_weekly_report)
        self.search_frame.monthly_clicked.connect(self.show_monthly_report)
        
        # 初始化布局几何
        self.updateLayout()
        
        # 用于淡入淡出动画的透明度效果
        self.op = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.op)
        self.op.setOpacity(0.0)
        self.anim_group = None
        self.geo_anim = None
        self.anim_type = None

        # 监控鼠标位置的定时器
        self.monitor_timer = QtCore.QTimer(self)
        self.monitor_timer.setInterval(100)  # 100ms 检测一次
        self.monitor_timer.timeout.connect(self._checkMousePos)
        self.ball_ref = None
        
        # 报告窗口引用
        self.daily_report_window = None
        self.weekly_report_window = None
        self.monthly_report_window = None

    def close_other_reports(self, exclude=None):
        if exclude != 'daily' and self.daily_report_window is not None and self.daily_report_window.isVisible():
            self.daily_report_window.close()
        if exclude != 'weekly' and self.weekly_report_window is not None and self.weekly_report_window.isVisible():
            self.weekly_report_window.close()
        if exclude != 'monthly' and self.monthly_report_window is not None and self.monthly_report_window.isVisible():
            self.monthly_report_window.close()

    def show_daily_report(self):
        try:
            from ui.component.report.daily_sum import SimpleDailyReport
            self.close_other_reports(exclude='daily')
            if self.daily_report_window is None or not self.daily_report_window.isVisible():
                self.daily_report_window = SimpleDailyReport()
                self.daily_report_window.clicked.connect(self.daily_report_window.close)
            self.daily_report_window.show()
        except Exception as e:
            print(f"Error showing daily report: {e}")

    def show_weekly_report(self):
        try:
            from ui.component.report.week_sum import WeeklyDashboard
            self.close_other_reports(exclude='weekly')
            if self.weekly_report_window is None or not self.weekly_report_window.isVisible():
                self.weekly_report_window = WeeklyDashboard()
                self.weekly_report_window.clicked.connect(self.weekly_report_window.close)
            self.weekly_report_window.show()
        except Exception as e:
            print(f"Error showing weekly report: {e}")

    def show_monthly_report(self):
        try:
            from ui.component.report.month_sum import MilestoneReport
            self.close_other_reports(exclude='monthly')
            if self.monthly_report_window is None or not self.monthly_report_window.isVisible():
                self.monthly_report_window = MilestoneReport()
                self.monthly_report_window.clicked.connect(self.monthly_report_window.close)
            self.monthly_report_window.show()
        except Exception as e:
            print(f"Error showing monthly report: {e}")

    def _checkMousePos(self):
        """
        检查鼠标是否在安全区域内（悬浮球 + 弹窗的包围盒）。
        如果在区域外，则执行隐藏。
        """
        if not self.isVisible() or not self.ball_ref:
            self.monitor_timer.stop()
            return

        pos = QtGui.QCursor.pos()
        
        # 获取几何信息（屏幕坐标）
        ball_geo = self.ball_ref.frameGeometry()
        popup_geo = self.frameGeometry()
        
        # 计算包围盒（并集）
        safe_rect = ball_geo.united(popup_geo)
        
        # 如果鼠标不在安全区域内，则执行隐藏
        if not safe_rect.contains(pos):
            self.monitor_timer.stop()
            self._performHide(self.ball_ref)

    def updateLayout(self):
        """
        根据当前尺寸更新子组件的布局。
        """
        w = self.orig_pix_size.width()
        h = self.orig_pix_size.height()
        mx, my = self.target_margin
        
        # 总尺寸：图片高度 + 垂直间距 + 球体高度（用于搜索框对齐）
        total_h = h + my + self.ball_size
        total_w = w
        
        self.resize(total_w, total_h)
        
        # 图片位于顶部
        self.label.setGeometry(0, 0, w, h)
        
        # 搜索框位于左下方
        # 宽度 = 总宽度 - 球体尺寸 - 水平间距（保持与垂直间距一致）
        gap = my  # 使用垂直间距作为搜索框与球体之间的水平间距
        sf_w = w - self.ball_size - gap
        sf_h = self.ball_size
        sf_y = h + my
        
        self.search_frame.setGeometry(0, sf_y, sf_w, sf_h)

    def resizeEvent(self, event):
        curr_size = self.size()
        curr_w = curr_size.width()
        curr_h = curr_size.height()
        
        # 假设保持大致的长宽比
        full_w = self.orig_pix_size.width()
        full_h = self.orig_pix_size.height() + self.target_margin[1] + self.ball_size
        
        if full_w == 0 or full_h == 0: return
        
        ratio_w = curr_w / full_w
        ratio_h = curr_h / full_h
        
        # 缩放图片
        img_w = int(self.orig_pix_size.width() * ratio_w)
        img_h = int(self.orig_pix_size.height() * ratio_h)
        self.label.setGeometry(0, 0, img_w, img_h)
        
        # 缩放间距
        orig_gap = self.target_margin[1]
        scaled_gap = int(orig_gap * ratio_h)
        
        # 缩放搜索框
        sf_w = int((self.orig_pix_size.width() - self.ball_size - orig_gap) * ratio_w)
        # 修改处：减小搜索框高度 (固定为 45px * 缩放比)
        sf_h = int(45 * ratio_h)
        sf_y = img_h + scaled_gap
        
        self.search_frame.setGeometry(0, sf_y, sf_w, sf_h)
        
        super().resizeEvent(event)

    def topLeftTarget(self, ball_widget):
        """
        计算整个 L 形控件的目标几何位置。
        图表位于小球上方，搜索框位于小球左侧。
        """
        br = ball_widget.frameGeometry()
        w = self.orig_pix_size.width()
        mx, my = self.target_margin
        h_img = self.orig_pix_size.height()
        total_h = h_img + my + self.ball_size
        
        # X轴：右边缘与小球对齐（即 Left = Ball.Right - w）
        x = br.right() - w
        
        # Y轴：图片底部位于 (Ball.Top - my)
        # 所以控件顶部 = (Ball.Top - my) - Image.Height
        y = br.top() - my - h_img
        
        # 屏幕边界检查
        screen = QtGui.QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = max(geo.left() + 4, min(x, geo.right() - w - 4))
        y = max(geo.top() + 4, min(y, geo.bottom() - total_h - 4))
        
        return QtCore.QRect(int(x), int(y), w, total_h)

    def stop_anim(self):
        """
        停止任何正在运行的动画。
        """
        if self.anim_group:
            try:
                self.anim_group.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.anim_group.stop()
            self.anim_group.deleteLater()
            self.anim_group = None
            self.geo_anim = None
            self.anim_type = None

    def showFromBall(self, ball_widget):
        """
        动画显示：从小球位置弹出。
        """
        self.stop_anim()
        self.monitor_timer.stop()  # 停止隐藏检测
        self.ball_ref = ball_widget # 更新引用
        self.anim_type = 'show'
        ball_widget.raise_()
        end_rect = self.topLeftTarget(ball_widget)
        
        w = end_rect.width()
        h = end_rect.height()
        start_w = int(w * 0.6)
        start_h = int(h * 0.6)
        
        # 从右下角锚点（即小球中心）展开
        anchor_x = end_rect.right()
        anchor_y = end_rect.bottom()
        
        start_x = anchor_x - start_w
        start_y = anchor_y - start_h
        start_rect = QtCore.QRect(start_x, start_y, start_w, start_h)

        self.setGeometry(start_rect)
        self.show()
        
        # 几何动画（大小和位置）
        self.geo_anim = QtCore.QPropertyAnimation(self, b"geometry")
        self.geo_anim.setStartValue(start_rect)
        self.geo_anim.setEndValue(end_rect)
        self.geo_anim.setDuration(360)
        self.geo_anim.setEasingCurve(QtCore.QEasingCurve.OutBack)
        
        # 透明度动画
        opacity_anim = QtCore.QPropertyAnimation(self.op, b"opacity")
        opacity_anim.setStartValue(self.op.opacity())
        opacity_anim.setEndValue(1.0)
        opacity_anim.setDuration(260)
        
        # 并行动画组
        self.anim_group = QtCore.QParallelAnimationGroup(self)
        self.anim_group.addAnimation(self.geo_anim)
        self.anim_group.addAnimation(opacity_anim)
        
        def on_finished():
            if self.anim_group:
                self.anim_group.deleteLater()
                self.anim_group = None
                self.geo_anim = None
                self.anim_type = None
        self.anim_group.finished.connect(on_finished)
        self.anim_group.start()

    def followBall(self, ball_widget):
        """
        跟随小球移动。
        """
        if not self.isVisible():
            return
        ball_widget.raise_()
        end_rect = self.topLeftTarget(ball_widget)
        
        if self.anim_group and self.geo_anim and self.anim_type:
            if self.anim_type == 'show':
                self.geo_anim.setEndValue(end_rect)
            elif self.anim_type == 'hide':
                anchor_x = end_rect.right()
                anchor_y = end_rect.bottom()
                w = end_rect.width()
                h = end_rect.height()
                end_w = int(w * 0.5)
                end_h = int(h * 0.5)
                end_x = anchor_x - end_w
                end_y = anchor_y - end_h
                target_small_rect = QtCore.QRect(end_x, end_y, end_w, end_h)
                self.geo_anim.setEndValue(target_small_rect)
        else:
             self.setGeometry(end_rect)

    def hideToBall(self, ball_widget):
        """
        请求隐藏：启动位置检测定时器。
        """
        if not self.isVisible():
            return
        self.ball_ref = ball_widget
        # 立即进行一次检查，如果不在范围内则开始计时或直接隐藏
        # 但为了平滑体验，直接启动定时器即可
        if not self.monitor_timer.isActive():
            self.monitor_timer.start()

    def _performHide(self, ball_widget):
        """
        实际执行隐藏动画：收回到小球位置。
        """
        self.stop_anim()
        self.anim_type = 'hide'
        
        end_rect = self.topLeftTarget(ball_widget)
        anchor_x = end_rect.right()
        anchor_y = end_rect.bottom()
        
        w = end_rect.width()
        h = end_rect.height()
        end_w = int(w * 0.5)
        end_h = int(h * 0.5)
        
        # 收缩到小球中心
        end_x = anchor_x - end_w
        end_y = anchor_y - end_h
        target_small_rect = QtCore.QRect(end_x, end_y, end_w, end_h)
        
        self.geo_anim = QtCore.QPropertyAnimation(self, b"geometry")
        self.geo_anim.setStartValue(self.geometry())
        self.geo_anim.setEndValue(target_small_rect)
        self.geo_anim.setDuration(240)
        self.geo_anim.setEasingCurve(QtCore.QEasingCurve.InCubic)
        
        opacity_anim = QtCore.QPropertyAnimation(self.op, b"opacity")
        opacity_anim.setStartValue(self.op.opacity())
        opacity_anim.setEndValue(0.0)
        opacity_anim.setDuration(220)
        
        self.anim_group = QtCore.QParallelAnimationGroup(self)
        self.anim_group.addAnimation(self.geo_anim)
        self.anim_group.addAnimation(opacity_anim)
        def done():
            self.hide()
            if self.anim_group:
                self.anim_group.deleteLater()
                self.anim_group = None
                self.geo_anim = None
                self.anim_type = None
        self.anim_group.finished.connect(done)
        self.anim_group.start()
