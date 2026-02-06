# -*- coding: utf-8 -*-
import sys
import requests
from PySide6 import QtWidgets, QtCore, QtGui

class ModelSelectionDialog(QtWidgets.QDialog):
    def __init__(self, default_model="gpt-oss:20b-cloud", parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择 AI 模型")
        self.setFixedSize(400, 250)
        self.selected_model = default_model
        
        # 布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题说明
        title_label = QtWidgets.QLabel("请选择用于分析的 AI 模型:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 模型列表
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                font-size: 13px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        layout.addWidget(self.model_combo)
        
        # 状态标签
        self.status_label = QtWidgets.QLabel("正在获取本地模型...")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # 按钮区域
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QtWidgets.QPushButton("启动项目")
        self.start_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0069D9;
            }
            QPushButton:pressed {
                background-color: #0056B3;
            }
        """)
        self.start_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.start_btn)
        
        layout.addLayout(btn_layout)
        
        # 初始化数据
        self.default_model = default_model
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
                self.status_label.setStyleSheet("color: green; font-size: 12px;")
            else:
                self.status_label.setText("无法连接 Ollama，仅显示默认模型")
                self.status_label.setStyleSheet("color: orange; font-size: 12px;")
                
        except Exception as e:
            self.status_label.setText(f"连接失败: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-size: 12px;")
            
        # 填充下拉框
        self.model_combo.addItems(models)
        
        # 默认选中第一个
        self.model_combo.setCurrentIndex(0)

    def accept(self):
        """确认选择"""
        self.selected_model = self.model_combo.currentText()
        super().accept()

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
