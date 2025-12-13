try:
    from PySide6 import QtCore
except ImportError:
    from PyQt5 import QtCore

from ui.component.reminder import ReminderOverlay


class EntertainmentReminder(QtCore.QObject):
    def __init__(self, parent=None, threshold_duration=20):
        super().__init__(parent)
        self.threshold_duration = threshold_duration
        self.overlay = ReminderOverlay(parent)

    def on_status_update(self, result):
        status = result.get("status")
        duration = result.get("duration", 0)
        if status == "entertainment" and duration > self.threshold_duration:
            self.overlay.show_message("检测到您长时间处于娱乐状态，请注意休息！")

