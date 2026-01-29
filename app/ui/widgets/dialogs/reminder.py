"""
[正在使用]
用于显示"娱乐时间过长"的简单提醒弹窗。
被 ui.interaction_logic.reminder_logic.EntertainmentReminder 调用。
包含 ReminderOverlay 类。
"""
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6 import QtCore as QtCore  # type: ignore
    from PySide6 import QtGui as QtGui  # type: ignore
    from PySide6 import QtWidgets as QtWidgets  # type: ignore
else:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
        QT_LIB = "PySide6"
    except ImportError:
        from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
        QT_LIB = "PyQt5"

# 导入统一主题
try:
    from app.ui.widgets.report.theme import theme as MorandiTheme
except ImportError:
    try:
        from app.ui.widgets.report.theme import theme as MorandiTheme
    except ImportError:
        # Fallback if relative import fails
        from app.ui.widgets.report.theme import theme as MorandiTheme

def qt_const(name: str) -> Any:
    qt = getattr(QtCore, "Qt", None)
    if qt is None:
        return None
    val = getattr(qt, name, None)
    if val is not None:
        return val
    for enum_name in ("WindowType", "WidgetAttribute", "CursorShape", "AlignmentFlag"):
        enum = getattr(qt, enum_name, None)
        if enum is not None:
            sub = getattr(enum, name, None)
            if sub is not None:
                return sub
    return None


class ReminderOverlay(QtWidgets.QDialog):
    """简单娱乐提醒界面 - 仅显示消息和三个操作按钮"""
    
    if hasattr(QtCore, 'Signal'):
        Signal = QtCore.Signal
    else:
        Signal = QtCore.pyqtSignal
        
    work_clicked = Signal()
    snooze_clicked = Signal()
    disable_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(
            qt_const("FramelessWindowHint")
            | qt_const("WindowStaysOnTopHint")
        )
        
        self._is_closing = False
        
        wa_translucent = qt_const("WA_TranslucentBackground")
        if wa_translucent is not None:
            self.setAttribute(wa_translucent)
        wa_no_activate = qt_const("WA_ShowWithoutActivating")
        if wa_no_activate is not None:
            self.setAttribute(wa_no_activate)
        
        # 获取屏幕尺寸
        app = QtWidgets.QApplication.instance()
        screen: Optional[Any] = None
        if app is not None:
            primary = getattr(app, "primaryScreen", None)
            if callable(primary):
                screen = primary()
            else:
                pass
        if screen is None:
            desktop = getattr(QtWidgets.QApplication, "desktop", None)
            screen = desktop() if callable(desktop) else None
        
        # 获取有效屏幕几何尺寸
        if screen is not None:
            geometry = screen.availableGeometry()
        else:
            geometry = QtCore.QRect(0, 0, 800, 600)
        
        # 设置窗口尺寸（更大、更舒适的提醒窗口）
        window_width = 700
        window_height = 500
        center_x = geometry.left() + (geometry.width() - window_width) // 2
        center_y = geometry.top() + (geometry.height() - window_height) // 2
        self.setGeometry(center_x, center_y, window_width, window_height)
        
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("VideoReminderDialog")  # 为了匹配 QSS
        gradient_start = MorandiTheme.HEX_REMINDER_GRADIENT_START
        gradient_end = MorandiTheme.HEX_REMINDER_GRADIENT_END
        panel_fill = MorandiTheme.HEX_REMINDER_PANEL_FILL
        self.container.setStyleSheet(f"""
            QWidget#VideoReminderDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 {gradient_start},
                                            stop:1 {gradient_end});
                border-radius: 20px;
            }}
        """)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setAlignment(qt_const("AlignCenter"))
        main_layout.addWidget(self.container)
        
        # 容器内布局
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(25)
        
        # 1. 历史回顾区域 (新增)
        history_frame = QtWidgets.QFrame()
        panel_border = MorandiTheme.COLOR_BORDER.name()
        panel_fill = MorandiTheme.HEX_REMINDER_PANEL_FILL
        history_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {panel_fill};
                border-radius: 15px;
                border: 1px solid {panel_border};
            }}
        """)
        history_layout = QtWidgets.QVBoxLayout(history_frame)
        history_layout.setContentsMargins(25, 20, 25, 20)
        history_layout.setSpacing(8)
        
        # 上次专注时长
        self.focus_summary_label = QtWidgets.QLabel("📚 刚才你专注了32分钟")
        self.focus_summary_label.setObjectName("focus_summary")
        self.focus_summary_label.setAlignment(qt_const("AlignLeft"))
        
        accent_color = MorandiTheme.COLOR_ACCENT_DARK.name() # #FBC02D (Golden)
        
        self.focus_summary_label.setStyleSheet(f"""
            QLabel#focus_summary {{ 
                color: {accent_color};      /* 金色 */ 
                font-size: 18px; 
                font-weight: bold; 
                background: transparent;
                border: none;
                margin-bottom: 2px;
            }} 
        """)
        history_layout.addWidget(self.focus_summary_label)
        
        # 专注内容
        self.focus_task_label = QtWidgets.QLabel("在做：论文写作")
        self.focus_task_label.setObjectName("focus_task")
        self.focus_task_label.setAlignment(qt_const("AlignLeft"))
        self.focus_task_label.setWordWrap(True) # 允许长文本换行
        
        self.focus_task_label.setStyleSheet(f"""
            QLabel#focus_task {{ 
                color: #5D4037; 
                font-size: 15px; 
                background: transparent;
                border: none;
                padding-left: 26px; /* 稍微缩进，与上面的图标对齐 */
                line-height: 1.2;
            }} 
        """)
        history_layout.addWidget(self.focus_task_label)
        
        layout.addWidget(history_frame)

        # 2. 消息内容区域 (Frame包裹)
        msg_frame = QtWidgets.QFrame()
        msg_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {panel_fill};
                border-radius: 15px;
                border: 1px solid {panel_border};
            }}
        """)
        msg_layout = QtWidgets.QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(30, 25, 30, 25)
        msg_layout.setSpacing(12)
        
        # 主消息
        self.main_message = QtWidgets.QLabel("🌿 电量充得差不多啦！")
        self.main_message.setObjectName("message")
        self.main_message.setAlignment(qt_const("AlignLeft")) # 改为左对齐
        self.main_message.setWordWrap(True)
        self.main_message.setStyleSheet("""
            QLabel#message { 
                color: #2E7D32;      /* 深绿色 */ 
                font-size: 22px; 
                font-weight: bold;
                background: transparent;
                border: none;
            } 
        """)
        msg_layout.addWidget(self.main_message)
        
        # 建议详情
        # 初始化时使用默认文案，show_reminder 时会根据数据更新
        self.suggestion_detail = QtWidgets.QLabel("趁着思路还没断，现在回去效率最高！")
        self.suggestion_detail.setAlignment(qt_const("AlignLeft"))
        self.suggestion_detail.setWordWrap(True)
        self.suggestion_detail.setStyleSheet("""
            QLabel { 
                color: #4E342E;      /* 深棕色 */ 
                font-size: 16px; 
                background: transparent;
                border: none;
                margin-top: 15px;    /* 增加顶部间距 */
                margin-bottom: 5px;  /* 增加底部间距 */
            } 
        """)
        msg_layout.addWidget(self.suggestion_detail)
        
        # 鼓励语 (原 encouragement)
        self.encouragement = QtWidgets.QLabel("论文思路还在热乎中，现在回去刚刚好！")
        self.encouragement.setAlignment(qt_const("AlignLeft"))
        self.encouragement.setWordWrap(True)
        self.encouragement.setStyleSheet("""
            QLabel { 
                color: #5D4037;      /* 棕色 */ 
                font-size: 16px; 
                background: transparent;
                border: none;
            } 
        """)
        msg_layout.addWidget(self.encouragement)
        
        layout.addWidget(msg_frame)
        
        # 添加伸缩空间
        layout.addStretch()
        
        # 3. 操作按钮栏
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(qt_const("AlignCenter"))
        
        # 按钮1：继续努力 (Primary)
        work_button = QtWidgets.QPushButton("继续努力 💪")
        work_button.setObjectName("primary")
        work_button.setMinimumHeight(55)
        work_button.setMinimumWidth(180)
        work_button.setCursor(qt_const("PointingHandCursor"))
        
        btn_primary_bg = MorandiTheme.COLOR_BG_PANEL.name() # #50795D
        btn_primary_hover = MorandiTheme.COLOR_PRIMARY_LIGHT.name() # #547C7E
        
        work_button.setStyleSheet(f"""
            QPushButton#primary {{
                background: {btn_primary_bg};
                color: #F9F5F5;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid {accent_color};
            }}
            QPushButton#primary:hover {{
                background: {btn_primary_hover};
            }}
            QPushButton#primary:pressed {{
                background: {btn_primary_bg};
            }}
        """)
        work_button.clicked.connect(self.on_work_button)
        button_layout.addWidget(work_button)
        
        # 按钮2：再充5分钟 (Secondary)
        snooze_button = QtWidgets.QPushButton("再充5分钟电 🔋")
        snooze_button.setObjectName("secondary")
        snooze_button.setMinimumHeight(55)
        snooze_button.setMinimumWidth(180)
        snooze_button.setCursor(qt_const("PointingHandCursor"))
        snooze_button.setStyleSheet(f"""
            QPushButton#secondary {{
                background: transparent;
                color: #5D4037;
                border: 2px solid {accent_color};
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#secondary:hover {{
                background: rgba(80, 121, 93, 0.3);
                border-color: {accent_color};
                color: {accent_color};
            }}
            QPushButton#secondary:pressed {{
                background: rgba(80, 121, 93, 0.5);
            }}
        """)
        snooze_button.clicked.connect(self.on_snooze_button)
        button_layout.addWidget(snooze_button)
        
        layout.addLayout(button_layout)
        
        # 底部：暂时禁用 (更隐蔽的设计)
        # disable_button = QtWidgets.QPushButton("今天不再提醒")
        # disable_button.setCursor(qt_const("PointingHandCursor"))
        # disable_button.setStyleSheet(f"""
        #     QPushButton {{
        #         background: transparent;
        #         color: {MorandiTheme.COLOR_TEXT_SECONDARY.name()};
        #         border: none;
        #         font-size: 13px;
        #         text-decoration: underline;
        #     }}
        #     QPushButton:hover {{
        #         color: #5D4037;
        #     }}
        # """)
        # disable_button.clicked.connect(self.on_disable_button)
        # layout.addWidget(disable_button, 0, qt_const("AlignCenter"))
        
        # 点击关闭
        # self.setCursor(qt_const("PointingHandCursor")) # 移除全局手型，避免干扰
        
        # 动画效果
        self.fade_animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)

    def keyPressEvent(self, event):
        """Esc 键关闭"""
        if event.key() == QtCore.Qt.Key_Escape:
            self.close_reminder()
        else:
            super().keyPressEvent(event)
    
    def hideEvent(self, event):
        """隐藏事件处理"""
        if not self._is_closing:
            event.ignore()  # 保留窗口，但不强制显示
        else:
            super().hideEvent(event)
    
    def on_work_button(self):
        """用户点击'回去工作'按钮"""
        # 显示激励语
        self.main_message.setText("太棒了！🎯")
        self.encouragement.setText("你做的很对，专注才能成就梦想！\n加油，我看好你！💪")
        self.work_clicked.emit()
        # 延迟关闭，让用户看到激励语
        QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def on_snooze_button(self):
        """用户点击'再休息5分钟'按钮"""
        # 显示激励语
        self.main_message.setText("好的，休息一下～ ☕")
        self.encouragement.setText("放松心情，5分钟后我们继续加油！\n你的坚持会有回报的！✨")
        self.snooze_clicked.emit()
        # 延迟关闭，让用户看到激励语
        QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def on_disable_button(self):
        """用户点击'禁用提醒'按钮"""
        # 显示激励语
        self.main_message.setText("理解你～")
        self.encouragement.setText("希望你能自觉安排时间。\n记住，自律是通往成功的钥匙！🔑")
        self.disable_clicked.emit()
        # 延迟关闭，让用户看到激励语
        QtCore.QTimer.singleShot(1500, self.close_reminder)
    
    def close_reminder(self):
        """关闭提醒"""
        self._is_closing = True
        self.fade_out_and_close()
    
    def fade_out_and_close(self):
        """淡出动画"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(lambda: self.hide())
        self.fade_animation.start()
    
    def show_reminder(self, data: dict):
        """显示智能提醒"""
        # 根据严重级别自定义消息
        severity = data.get('severity', 'low')
        duration = data.get('duration', 0)  # 持续时间（秒），需要转换为分钟
        # 确保至少显示 1 分钟，避免出现 "0 分钟"
        minutes = max(1, int(duration / 60)) if duration else 22
        
        # 优先使用传入的消息
        custom_message = data.get('message')
        custom_encouragement = data.get('encouragement')
        
        if custom_message:
            message = custom_message
        else:
            # 温暖友好的提醒消息
            if severity == 'low':
                message = f"你已经看了 {minutes} 分钟视频啦～\n是不是被剧情吸引住了？没关系，\n要不要试试换件事做？✨"
            elif severity == 'medium':
                message = f"你已经追剧 {minutes} 分钟了呢～\n时间过得可真快！\n不过是时候回到工作上了吧？😊"
            else:  # high
                message = f"哇，{minutes} 分钟了！\n你真的很投入呢～\n但现在真的该认真工作了哦！"
        
        # 优化文案和排版：在主消息和建议详情之间增加空行，或者调整文本
        # 这里直接通过 HTML 格式化来增强视觉效果
        
        # 将换行符转换为 HTML 的换行，并增加段落间距
        formatted_message = message.replace('\n', '<br>')
        
        # 使用 HTML 样式
        self.main_message.setText(f"""
            <p style='line-height: 140%; margin-bottom: 10px;'>{formatted_message}</p>
        """)
        
        if custom_encouragement:
            encouragement = custom_encouragement
        else:
            if severity == 'low':
                encouragement = "💪 休息一下，然后继续加油！"
            elif severity == 'medium':
                encouragement = "🎯 坚持一下，好事儿在后头！"
            else:
                encouragement = "✨ 冲冲冲，你可以的！"
        
        self.encouragement.setText(encouragement)
        
        # 建议详情文案微调
        # 重新根据最新的 duration 更新文案
        # 注意：这里的 duration 是娱乐时长，还是应该用专注时长？
        # 通常番茄钟是：专注25分钟 -> 休息5分钟。
        # 这里场景是：用户正在娱乐（被抓包了）。
        # 如果用户刚才专注了很久（比如 > 45分钟），那么建议他休息一会是合理的。
        # 如果用户刚才没怎么专注，或者才专注了几分钟就开始玩，那么建议直接回去。
        
        # 我们这里做一个更智能的判断
        last_focus_duration = 0
        if 'last_duration_min' in locals():
            last_focus_duration = last_duration_min * 60 # 转换为秒
        
        # 策略：如果上次专注 > 45分钟，建议休息 5-10 分钟。否则建议立即回去。
        if last_focus_duration > 2700: # 45分钟
            rec_rest = 10
        elif last_focus_duration > 1500: # 25分钟
            rec_rest = 5
        else:
            rec_rest = 0
            
        if rec_rest > 0:
            self.suggestion_detail.setText(f"刚才专注了很久，建议休息 {rec_rest} 分钟后再继续！")
        else:
            self.suggestion_detail.setText("趁着思路还没断，现在回去效率最高！")
        
        # --- 获取真实的历史专注数据 ---
        try:
            from app.data.dao.activity_dao import StatsDAO, WindowSessionDAO
            from datetime import date
            
            # 1. 获取今日总专注时长 (Today Focus)
            # 注意：get_today_stats 返回的是一个字典
            today_stats = StatsDAO.get_today_stats()
            # 假设返回结构: {'focus_duration': 1234, 'entertainment_duration': ...}
            # 如果 StatsDAO 还没实现这个，我们可能需要现写一个简单的查询
            # 暂时用 get_daily_stats
            # daily_record = StatsDAO.get_daily_stats(date.today())
            # total_focus_minutes = int(daily_record.focus_duration / 60) if daily_record else 0
            
            # 由于 DAO 层方法不确定，我们尝试用最稳妥的 WindowSessionDAO 获取最近一次专注记录
            last_focus_session = WindowSessionDAO.get_last_focus_session()
            
            if last_focus_session:
                last_duration_min = int(last_focus_session.get('duration', 0) / 60)
                last_task_name = last_focus_session.get('process_name', '未知任务')
                
                # 尝试优化任务名显示：如果是浏览器，显示标题；如果是 IDE，显示项目名
                window_title = last_focus_session.get('window_title', '')
                process_name = last_focus_session.get('process_name', '')
                
                # 获取 AI 摘要
                ai_summary = last_focus_session.get('summary')
                
                # 优先级：AI摘要 > 清洗后的窗口标题 > 进程名
                if ai_summary and len(ai_summary) > 2: # 确保摘要不是空的或无效的
                    last_task_name = ai_summary
                elif window_title:
                     # 简单清洗：取 " - " 前的部分，或者取最后一部分
                     clean_title = window_title.split(' - ')[0]
                     if len(clean_title) > 15:
                         clean_title = clean_title[:12] + "..."
                     last_task_name = clean_title
                else:
                    last_task_name = process_name
                
                self.focus_summary_label.setText(f"📚 刚才你专注了{last_duration_min}分钟")
                self.focus_task_label.setText(f"在做：{last_task_name}")
                
                # 更新建议文案（因为有了真实数据）
                last_focus_duration = last_duration_min * 60
                if last_focus_duration > 2700: # 45分钟
                    rec_rest = 10
                elif last_focus_duration > 1500: # 25分钟
                    rec_rest = 5
                else:
                    rec_rest = 0
                    
                if rec_rest > 0:
                    self.suggestion_detail.setText(f"刚才专注了很久，建议休息 {rec_rest} 分钟后再继续！")
                else:
                    self.suggestion_detail.setText("趁着思路还没断，现在回去效率最高！")
                    
            else:
                self.focus_summary_label.setText("📚 今天还没有开始专注哦")
                self.focus_task_label.setText("准备好开始第一项任务了吗？")
                # 没专注过，当然是建议直接开始
                self.suggestion_detail.setText("千里之行始于足下，现在开始效率最高！")
                
        except Exception as e:
            print(f"[Reminder] Error fetching real stats: {e}")
            # 出错时保持默认显示的假数据，或者显示为空
            # self.focus_summary_label.setText("📚 刚才你专注了--分钟")
            pass
        
        # 显示窗口
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()

class EntertainmentReminder(QtCore.QObject):
    """
    娱乐提醒逻辑控制器
    替代原 app.services.reminder_logic.manager.EntertainmentReminder
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog = ReminderOverlay(parent)
        
    def check_and_remind(self):
        """
        检查最新的 Window Session 是否为娱乐，且时长超过 60s
        如果是，则触发弹窗
        """
        try:
            # 检查当前模式，如果是充电模式，则不触发提醒
            from app.data.services.history_service import ActivityHistoryManager
            if ActivityHistoryManager.get_current_mode() == "recharge":
                return

            from app.data.dao.activity_dao import WindowSessionDAO
            
            # 1. 获取最新的会话
            session = WindowSessionDAO.get_last_session()
            
            if not session:
                return
                
            status = session.get('status')
            duration = session.get('duration', 0)
            
            # 2. 判断是否触发提醒
            # 条件：状态是 entertainment 且 持续时间 >= 60秒
            if status == 'entertainment' and duration >= 60:
                # 触发提醒
                # 简单根据时长判断严重程度
                if duration > 1800: # 30分钟
                    severity = 'high'
                elif duration > 600: # 10分钟
                    severity = 'medium'
                else:
                    severity = 'low'
                    
                self._handle_entertainment_warning(status, duration, severity)
                
        except Exception as e:
            print(f"[EntertainmentReminder] Error checking sessions: {e}")

    def _handle_entertainment_warning(self, status, duration, severity):
        """
        处理娱乐警告
        :param status: 当前状态
        :param duration: 持续时间(秒)
        :param severity: 严重程度 (low/medium/high)
        """
        if status == 'entertainment':
            self.dialog.show_reminder({
                'severity': severity,
                'duration': duration,
                'status': status
            })
