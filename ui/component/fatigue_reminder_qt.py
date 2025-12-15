from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal
from PySide6.QtGui import QFont, QColor, QPainter

class SuggestionCard(QtWidgets.QWidget):
    clicked = Signal(str, int)

    def __init__(self, icon, title, description, duration_text, parent=None):
        super().__init__(parent)
        self.icon = icon
        self.title = title
        self.description = description
        self.duration_text = duration_text
        self.is_active = False
        self.is_hovered = False
        self.countdown_timer = None
        self.remaining_seconds = 0

        self.setMinimumHeight(110)
        self.setCursor(Qt.PointingHandCursor)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Icon
        self.icon_label = QtWidgets.QLabel(icon)
        self.icon_label.setFont(QFont("Arial", 32))
        self.icon_label.setFixedSize(60, 60)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        # Text Layout
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(6)
        
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #2c3e50;")
        text_layout.addWidget(self.title_label)

        self.desc_label = QtWidgets.QLabel(description)
        self.desc_label.setFont(QFont("Microsoft YaHei", 12))
        self.desc_label.setStyleSheet("color: #666;")
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.desc_label)

        self.countdown_label = QtWidgets.QLabel("")
        self.countdown_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #27ae60;")
        text_layout.addWidget(self.countdown_label)

        layout.addLayout(text_layout, 1)

        # Duration
        self.duration_label = QtWidgets.QLabel(duration_text)
        self.duration_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.duration_label.setStyleSheet("color: #3498db;")
        self.duration_label.setAlignment(Qt.AlignCenter)
        self.duration_label.setFixedWidth(70)
        layout.addWidget(self.duration_label)

        self.update_style()

    def update_style(self):
        if self.is_active:
            self.setStyleSheet("""
                SuggestionCard {
                    background: linear-gradient(135deg, #e8f8f5 0%, #c8f0ea 100%);
                    border: 2px solid #27ae60;
                    border-radius: 12px;
                }
            """)
        elif self.is_hovered:
            self.setStyleSheet("""
                SuggestionCard {
                    background: linear-gradient(135deg, #ecf0f1 0%, #f8f9fa 100%);
                    border: 2px solid #3498db;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(52, 152, 219, 0.15);
                }
            """)
        else:
            self.setStyleSheet("""
                SuggestionCard {
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 12px;
                }
            """)

    def start_countdown(self, minutes):
        self.is_active = True
        self.remaining_seconds = minutes * 60
        self.update_style()

        if self.countdown_timer:
            self.countdown_timer.stop()
        
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start(1000)
        self._update_countdown()

    def stop_countdown(self):
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.countdown_label.setText("")
        self.is_active = False
        self.update_style()

    def _update_countdown(self):
        if self.remaining_seconds <= 0:
            self.stop_countdown()
            return
        
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.countdown_label.setText(f"倒计时: {mins}分{secs:02d}秒")
        self.remaining_seconds -= 1

    def mousePressEvent(self, event):
        if not self.is_active:
            # Parse minutes
            import re
            match = re.search(r'(\d+)', self.duration_text)
            minutes = int(match.group(1)) if match else 10
            self.clicked.emit(self.title, minutes)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.is_hovered = True
        self.update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update_style()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        # Required for stylesheet to work on custom QWidget
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)


class FatigueReminderWindow(QtWidgets.QWidget):
    suggestion_selected = Signal(str, int)
    window_closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("疲惫提醒")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.active_card = None
        self.is_closing = False
        
        self.init_ui()
        self.center_window()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignCenter)

        # Dialog Container
        self.dialog = QtWidgets.QWidget(self)
        self.dialog.setObjectName("dialog")
        self.dialog.setStyleSheet("""
            QWidget#dialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #e8f4f8, stop:1 #f0f7ff);
                border: 2px solid #3498db;
                border-radius: 20px;
            }
        """)
        
        dialog_layout = QtWidgets.QVBoxLayout(self.dialog)
        dialog_layout.setContentsMargins(50, 50, 50, 50)
        dialog_layout.setSpacing(28)

        # Header
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(20)
        
        icon_label = QtWidgets.QLabel("😴")
        icon_label.setFont(QFont("Arial", 56))
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(icon_label)

        title_layout = QtWidgets.QVBoxLayout()
        title_layout.setSpacing(8)
        
        title_label = QtWidgets.QLabel("检测到疲劳迹象")
        title_label.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title_label.setStyleSheet("color: #e74c3c;")
        title_layout.addWidget(title_label)

        self.duration_label = QtWidgets.QLabel("")
        self.duration_label.setFont(QFont("Microsoft YaHei", 14))
        self.duration_label.setStyleSheet("color: #2980b9;")
        title_layout.addWidget(self.duration_label)
        
        # Add stretch to push to top
        title_layout.addStretch()

        header_layout.addLayout(title_layout, 1)
        dialog_layout.addLayout(header_layout)
        title_layout.addWidget(self.duration_label)

        header_layout.addLayout(title_layout, 1)
        dialog_layout.addLayout(header_layout)

        # Tip
        tip_label = QtWidgets.QLabel(
            "💡 检测到您已连续工作较长时间，建议现在休息一下，有利于提高工作效率！"
        )
        tip_label.setFont(QFont("Microsoft YaHei", 13))
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("""
            QLabel {
                background-color: #fff9e6;
                border-left: 4px solid #f39c12;
                padding: 12px 16px;
                border-radius: 8px;
                color: #555;
            }
        """)
        dialog_layout.addWidget(tip_label)

        # Suggestions Label
        sugg_label = QtWidgets.QLabel("休息建议:")
        sugg_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        sugg_label.setStyleSheet("color: #2c3e50;")
        dialog_layout.addWidget(sugg_label)

        # Suggestions List
        self.suggestions_layout = QtWidgets.QVBoxLayout()
        self.suggestions_layout.setSpacing(12)
        self.create_suggestion_cards()
        dialog_layout.addLayout(self.suggestions_layout)

        # Buttons
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setSpacing(12)

        continue_btn = QtWidgets.QPushButton("继续工作")
        continue_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        continue_btn.setCursor(Qt.PointingHandCursor)
        continue_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover { background: #2980b9; }
            QPushButton:pressed { background: #1f618d; }
        """)
        continue_btn.clicked.connect(self.close_reminder)

        snooze_btn = QtWidgets.QPushButton("5分钟后提醒")
        snooze_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        snooze_btn.setCursor(Qt.PointingHandCursor)
        snooze_btn.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover { background: #d35400; }
            QPushButton:pressed { background: #b83000; }
        """)
        snooze_btn.clicked.connect(self.close_reminder)

        settings_btn = QtWidgets.QPushButton("⚙️ 设置")
        settings_btn.setFont(QFont("Microsoft YaHei", 12))
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover { background: #7f8c8d; }
        """)

        buttons_layout.addWidget(continue_btn)
        buttons_layout.addWidget(snooze_btn)
        buttons_layout.addWidget(settings_btn)
        dialog_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.dialog)

        # Animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(400)
        self.fade_animation.finished.connect(self.on_fade_finished)

    def create_suggestion_cards(self):
        suggestions = [
            ("🚶", "散步", "走动一下，活动筋骨", "10 分钟"),
            ("💧", "补充水分", "喝杯温水，缓解疲劳", "5 分钟"),
            ("👀", "远眺放松", "看看远处，缓解眼疲劳", "3 分钟"),
            ("🧘", "冥想调息", "深呼吸冥想，放松身心", "15 分钟"),
        ]
        
        self.cards = []
        for icon, title, desc, duration in suggestions:
            card = SuggestionCard(icon, title, desc, duration, self.dialog)
            card.clicked.connect(self.on_suggestion_clicked)
            self.suggestions_layout.addWidget(card)
            self.cards.append(card)

    def center_window(self):
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            width = 950
            height = 750
            x = geom.left() + (geom.width() - width) // 2
            y = geom.top() + (geom.height() - height) // 2
            self.setGeometry(x, y, width, height)

    def show_reminder(self, duration=0):
        if duration > 0:
            mins = duration // 60
            self.duration_label.setText(f"已工作 {mins} 分钟")
        
        self.setWindowOpacity(0.0)
        self.show()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def close_reminder(self):
        if not self.is_closing:
            self.is_closing = True
            self.fade_animation.setStartValue(self.windowOpacity())
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.start()

    def on_fade_finished(self):
        if self.is_closing:
            self.hide()
            self.is_closing = False
            self.window_closed.emit()

    def on_suggestion_clicked(self, title, minutes):
        # Stop others
        for card in self.cards:
            card.stop_countdown()
        
        # Start clicked
        sender = self.sender()
        if sender:
            sender.start_countdown(minutes)
            self.active_card = sender
        
        self.suggestion_selected.emit(title, minutes)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100)) # Semi-transparent background
