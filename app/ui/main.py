import sys
from PySide6 import QtCore, QtWidgets
from app.ui.manager import FlowStateApp

def main(msg_queue=None):
    try:
        if hasattr(QtCore.Qt, 'AA_ShareOpenGLContexts'):
            QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    
    # 初始化应用管理器
    flow_manager = FlowStateApp(msg_queue)
    
    # 尝试预加载日报模块（如果可用）
    try:
        from app.ui.widgets.report import daily as daily_sum
    except Exception:
        pass

    app.setQuitOnLastWindowClosed(False)
    exit_code = app.exec()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()