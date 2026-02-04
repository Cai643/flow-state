try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal

from app.ui.widgets.focus_card import FocusStatusCard
from app.ui.widgets.history_report import HistoryEntryWidget

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



class CardPopup(QtWidgets.QWidget):
    """
    包含图表和搜索框的弹出窗口。
    负责管理布局、定位和动画效果。
    """
    request_full_report = Signal()

    def __init__(self, target_margin=(5, 7), ball_size=64):
        super().__init__()
        # 设置窗口标志：无边框 | 工具窗口（不在任务栏显示） | 始终置顶
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint
        )
        # 设置背景透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.target_margin = target_margin
        self.ball_size = ball_size
        
        # 专注状态卡片：联动监控结果与悬浮球
        self.card = FocusStatusCard(self)
        self.orig_pix_size = self.card.sizeHint()
        
        # 历史记录入口组件 (时光回溯)
        self.history_entry = HistoryEntryWidget(self)
        self.history_entry.daily_clicked.connect(self.show_daily_report)
        
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
        
        # 交互标志位：如果在进行交互（如输入），则暂停自动隐藏
        self.is_interacting = False
        
        # 报告窗口引用
        self.daily_report_window = None

    def update_focus_status(self, result: dict):
        """
        将监控线程的状态结果转发给专注卡片
        """
        if hasattr(self, "card") and self.card is not None:
            self.card.update_from_result(result)

    def close_other_reports(self, exclude=None):
        if exclude != 'daily' and self.daily_report_window is not None and self.daily_report_window.isVisible():
            self.daily_report_window.close()

    def show_daily_report(self):
        try:
            from app.ui.widgets.report.daily import SimpleDailyReport
            self.close_other_reports(exclude='daily')
            if self.daily_report_window is None or not self.daily_report_window.isVisible():
                self.daily_report_window = SimpleDailyReport()
                self.daily_report_window.clicked.connect(self.daily_report_window.close)
            self.daily_report_window.show()
        except Exception as e:
            print(f"Error showing daily report: {e}")

    def _checkMousePos(self):
        """
        检查鼠标是否在安全区域内（悬浮球 + 弹窗的包围盒）。
        如果在区域外，则执行隐藏。
        """
        if not self.isVisible() or not self.ball_ref:
            self.monitor_timer.stop()
            return

        # 如果正在进行交互（如弹出对话框），则暂停检测
        if getattr(self, 'is_interacting', False):
            return

        # 关键修正：如果当前有活动的弹出窗口（如 QComboBox 的下拉列表），则不执行隐藏
        if QtWidgets.QApplication.activePopupWidget():
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
            
            # 隐藏时重置历史记录组件到长条状态
            if hasattr(self, "history_entry"):
                self.history_entry.reset()
        else:
            # 如果鼠标在安全区域内（例如移到了上方的卡片或球体），但不在历史组件内，且历史组件已展开，则重置回长条
            if hasattr(self, "history_entry"):
                # 检查是否处于展开状态 (bar 隐藏即为展开)
                is_expanded = not self.history_entry.bar.isVisible()
                if is_expanded:
                    # 将全局坐标转换为历史组件的局部坐标
                    local_pos = self.history_entry.mapFromGlobal(pos)
                    # 如果鼠标不在历史组件的矩形范围内（包括图标和间隙）
                    if not self.history_entry.rect().contains(local_pos):
                        self.history_entry.reset()

            # 如果还在安全区域内，但大小可能因为卡片展开而变化，
            # 需要检查是否需要更新位置（向上生长）
            if hasattr(self, "card") and self.card:
                target_rect = self.topLeftTarget(self.ball_ref)
                if target_rect != self.geometry():
                    # 平滑移动过去
                    if not self.geo_anim:
                        self.geo_anim = QtCore.QPropertyAnimation(self, b"geometry")
                    
                    if self.geo_anim.state() != QtCore.QAbstractAnimation.Running:
                        self.geo_anim.setStartValue(self.geometry())
                        self.geo_anim.setEndValue(target_rect)
                        self.geo_anim.setDuration(200) # 快速调整
                        self.geo_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
                        self.geo_anim.start()

    def updateLayout(self):
        """
        根据当前尺寸更新子组件的布局。
        """
        w = self.orig_pix_size.width()
        h = self.orig_pix_size.height()
        mx, my = self.target_margin
        
        # 确保宽度足以容纳历史组件 (sizeHint=230)
        # 最小宽度 = 历史组件宽(230) + 间距 + 球体宽
        history_min_w = 230
        min_w = history_min_w + mx + self.ball_size
        
        total_w = max(w, min_w)
        
        # 总尺寸：专注卡片高度 + 间距 + 球体高度 (历史组件占据球体高度的左侧)
        # 确保底部高度足以容纳历史组件 (sizeHint=64)
        history_h = 64
        bottom_h = max(self.ball_size, history_h)
        total_h = h + my + bottom_h
        
        self.resize(total_w, total_h)
        
        # 专注卡片位于顶部，拉伸以适应宽度
        self.card.setGeometry(0, 0, total_w, h)
        
        # 历史入口位于左下方
        sf_y = h + my
        sf_w = total_w - self.ball_size - mx
        
        self.history_entry.setGeometry(0, sf_y, sf_w, bottom_h)

    def resizeEvent(self, event):
        w = self.width()
        h = self.height()
        mx, my = self.target_margin
        
        # 底部区域高度 = 球体大小 (或历史组件高度)
        # 确保底部高度足以容纳历史组件 (sizeHint=64)
        history_h = 64
        bottom_h = max(self.ball_size, history_h)
        
        # 卡片高度 = 总高度 - 间距 - 底部高度
        card_h = h - my - bottom_h
        
        if card_h > 0:
            self.card.setGeometry(0, 0, w, card_h)
            
        # 历史入口位置：左下方
        sf_y = card_h + my
        # 历史入口宽度 = 总宽度 - 球体宽度 - 间距
        sf_w = w - self.ball_size - mx
        
        self.history_entry.setGeometry(0, sf_y, sf_w, bottom_h)
        
    def topLeftTarget(self, ball_widget):
        """
        计算整个 L 形控件的目标几何位置。
        图表位于小球上方，历史入口位于小球左侧。
        """
        br = ball_widget.frameGeometry()
        
        # 使用 card 的 sizeHint 来决定弹窗大小，实现自适应
        if hasattr(self, "card") and self.card:
             hint = self.card.sizeHint()
             # 确保宽度计算与 updateLayout 一致
             w_card = hint.width()
             h_card = hint.height()
             
             history_min_w = 230
             mx, my = self.target_margin
             min_w = history_min_w + mx + self.ball_size
             w = max(w_card, min_w)
        else:
             w = self.orig_pix_size.width()
             h_card = self.orig_pix_size.height()

        mx, my = self.target_margin
        
        # 确保底部高度足以容纳历史组件 (sizeHint=64)
        history_h = 64
        bottom_h = max(self.ball_size, history_h)
        total_h = h_card + my + bottom_h
        
        # X轴：右边缘与小球对齐（即 Left = Ball.Right - w）
        x = br.right() - w
        
        # Y轴：图片底部位于 (Ball.Top - my)
        # 所以控件顶部 = (Ball.Top - my) - Image.Height
        y = br.top() - my - h_card
        
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
        
        # 强制让内部卡片更新一次可见性，确保尺寸正确
        if hasattr(self, "card") and self.card:
            # 重新获取更新后的尺寸
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
            
            # 动画结束后启动检测定时器，实现"离开即收回"
            if not self.monitor_timer.isActive():
                self.monitor_timer.start()
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
        if hasattr(self, "card") and self.card:
            try:
                self.card.reset_to_dashboard()
            except Exception:
                pass
        
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
