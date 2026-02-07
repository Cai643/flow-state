# -*- coding: utf-8 -*-
import sys
import requests
from PySide6 import QtWidgets, QtCore, QtGui

class CustomTitleBar(QtWidgets.QWidget):
    """自定义标题栏"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setSpacing(10)

        # 图标 (可选，这里先用色块代替或不加)
        # self.icon_label = QtWidgets.QLabel()
        # self.icon_label.setFixedSize(16, 16)
        # self.icon_label.setStyleSheet("background-color: #96C24B; border-radius: 8px;")
        # self.layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("""
            color: #5D4037;
            font-family: "Microsoft YaHei";
            font-size: 13px;
            font-weight: bold;
        """)
        self.layout.addWidget(self.title_label)
        self.layout.addStretch()

        # 关闭按钮
        self.close_btn = QtWidgets.QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5D4037;
                font-size: 18px;
                border: none;
                font-weight: bold;
                margin-top: -2px; 
            }
            QPushButton:hover {
                color: #C62828;
            }
        """)
        # 连接信号由父窗口处理
        self.layout.addWidget(self.close_btn)

class ModelSelectionDialog(QtWidgets.QDialog):
    def __init__(self, default_model="gpt-oss:20b-cloud", parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 260)
        
        self.selected_model = default_model
        self.default_model = default_model
        
        # 主布局容器 (用于绘制圆角和背景)
        self.container = QtWidgets.QWidget(self)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self.container.setObjectName("container")
        
        # 布局
        self.main_layout = QtWidgets.QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. 标题栏
        self.title_bar = CustomTitleBar("选择 AI 模型", self)
        self.title_bar.close_btn.clicked.connect(self.reject)
        self.main_layout.addWidget(self.title_bar)
        
        # 2. 内容区域
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(25, 20, 25, 20)
        self.content_layout.setSpacing(15)
        
        # 标题说明
        title_label = QtWidgets.QLabel("请选择用于分析的 AI 模型:")
        title_label.setStyleSheet("""
            color: #5D4037;
            font-family: "Microsoft YaHei";
            font-size: 14px; 
            font-weight: bold;
        """)
        self.content_layout.addWidget(title_label)
        
        # 模型列表
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setCursor(QtCore.Qt.PointingHandCursor)
        # 样式表：Warm Light Theme
        self.model_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                font-family: "Microsoft YaHei";
                font-size: 13px;
                color: #5D4037;
                background-color: #FFFFFF;
                border: 2px solid #96C24B;
                border-radius: 6px;
            }
            QComboBox:hover {
                border-color: #7AA97D;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #96C24B;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #96C24B;
                background-color: #FFFFFF;
                color: #5D4037;
                selection-background-color: #D4E0BB;
                selection-color: #5D4037;
                outline: none;
                padding: 4px;
            }
        """)
        # 设置视图样式以确保文字可见
        view = QtWidgets.QListView()
        view.setStyleSheet("QListView::item { height: 28px; padding: 2px; }")
        self.model_combo.setView(view)
        
        self.content_layout.addWidget(self.model_combo)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel("正在获取本地模型...")
        self.status_label.setStyleSheet("color: #8D6E63; font-size: 12px; font-family: 'Microsoft YaHei';")
        self.content_layout.addWidget(self.status_label)
        
        self.content_layout.addStretch()
        
        # 按钮区域
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QtWidgets.QPushButton("启动项目")
        self.start_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.start_btn.setFixedSize(100, 36)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #96C24B;
                color: #FFFFFF;
                border: none;
                border-radius: 18px;
                font-family: "Microsoft YaHei";
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7AA97D;
            }
            QPushButton:pressed {
                background-color: #558B2F;
            }
        """)
        self.start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.start_btn)
        
        self.content_layout.addLayout(btn_layout)
        
        self.main_layout.addWidget(self.content_widget)
        
        # 设置整体样式
        self.container.setStyleSheet("""
            #container {
                background-color: #FEFAE0;
                border: 2px solid #96C24B;
                border-radius: 10px;
            }
            CustomTitleBar {
                background-color: #D4E0BB;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

        # 拖动相关变量
        self._dragging = False
        self._drag_start_pos = QtCore.QPoint()

        # 初始化数据
        self.load_models()

    def load_models(self):
        """加载本地 Ollama 模型"""
        models = [self.default_model]
        
        try:
            # 尝试从 Ollama API 获取模型列表
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [m['name'] for m in data.get('models', [])]
                
                # 去重并添加到列表
                for m in ollama_models:
                    if m != self.default_model:
                        models.append(m)
                
                self.status_label.setText(f"已加载 {len(ollama_models)} 个本地模型")
                self.status_label.setStyleSheet("color: #558B2F; font-size: 12px; font-family: 'Microsoft YaHei';")
            else:
                self.status_label.setText("无法连接 Ollama，仅显示默认模型")
                self.status_label.setStyleSheet("color: #FB8C00; font-size: 12px; font-family: 'Microsoft YaHei';")
                
        except Exception as e:
            self.status_label.setText(f"连接失败: {str(e)}")
            self.status_label.setStyleSheet("color: #D32F2F; font-size: 12px; font-family: 'Microsoft YaHei';")
            
        # 填充下拉框
        self.model_combo.addItems(models)
        
        # 默认选中第一个
        self.model_combo.setCurrentIndex(0)

    def accept(self):
        """确认选择"""
        self.selected_model = self.model_combo.currentText()
        super().accept()

    # --- 拖动逻辑 ---
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # 只有点击标题栏区域才能拖动
            if self.title_bar.geometry().contains(event.pos()):
                self._dragging = True
                self._drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & QtCore.Qt.LeftButton):
            self.move(event.globalPos() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

def show_model_selection():
    """显示模型选择对话框并返回选择的模型"""
    # 检查是否已经有 QApplication 实例
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        
    dialog = ModelSelectionDialog()
    if dialog.exec() == QtWidgets.QDialog.Accepted:
        return dialog.selected_model
    return None
