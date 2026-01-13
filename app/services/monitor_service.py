import time
try:
    from PySide6 import QtCore
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore
    Signal = QtCore.pyqtSignal

from app.services.ai.vision import CameraAnalyzer
from app.services.ai import inference as API
from app.data import ActivityHistoryManager

class MonitorThread(QtCore.QThread):
    status_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.analyzer = CameraAnalyzer()
        self.last_frame = None
        # 初始化历史管理器 (用于写入数据库)
        self.history_manager = ActivityHistoryManager()

    def run(self):
        if not self.analyzer.start():
            print("[MonitorThread] Failed to start camera. Exiting thread.")
            return

        while self.running:
            # 1. Capture Data
            frame = self.analyzer.capture_frame()
            analysis_stats = self.analyzer.analyze_frame(frame)
            content_type, change_val = self.analyzer.detect_content_type(frame, self.last_frame)
            self.last_frame = frame
            
            # 2. Prepare Data for API
            monitor_data = {
                'key_presses': 0, # Camera only mode, no input monitoring
                'mouse_clicks': 0,
                'screen_change_rate': change_val, # Now represents camera movement/change
                'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
            }

            # 3. Call API and Save Data
            if API:
                try:
                    result = API.get_analysis(monitor_data)
                    
                    # === 新增：保存状态到数据库 ===
                    status = result.get('status')
                    if status:
                        # 每次分析都尝试更新历史（history_manager 内部会处理去重和过滤）
                        self.history_manager.update(status)
                    
                    # 可以在这里添加 OCR 调用逻辑（当条件满足时）
                    # if should_perform_ocr(...):
                    #     text = ocr_service.recognize(frame)
                    #     self.history_manager.add_ocr_record(text, ...)

                    self.status_updated.emit(result)
                except Exception as e:
                    print(f"API Error: {e}")
            
            time.sleep(1) # Check every second

    def stop(self):
        self.running = False
        self.analyzer.stop()
        self.wait()
