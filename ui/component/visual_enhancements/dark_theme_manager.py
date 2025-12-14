"""
暗色主题管理器

负责管理应用程序的暗色系主题，包括颜色调色板、字体管理和样式表生成。
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
from typing import Dict, Optional
import colorsys


class DarkThemeManager(QtCore.QObject):
    """暗色主题管理器"""

    # 信号
    themeChanged = Signal()

    # 完整的暗色系颜色调色板
    COLORS = {
        # 背景色系
        'background_primary': '#1a1a1a',      # 主背景色 - 深黑色
        'background_secondary': '#2d2d2d',    # 次要背景色 - 中等灰色
        'background_card': '#3a3a3a',         # 卡片背景色 - 浅灰色
        'background_hover': '#4a4a4a',        # 悬停背景色
        'background_pressed': '#5a5a5a',      # 按下背景色

        # 文字色系
        'text_primary': '#FFFFFF',            # 主要文字颜色 - 纯白色
        'text_secondary': '#CCCCCC',          # 次要文字颜色 - 浅灰色
        'text_tertiary': '#999999',           # 三级文字颜色 - 中灰色
        'text_disabled': '#666666',           # 禁用文字颜色 - 深灰色

        # 强调色系
        'accent_green': '#a8d8ea',            # 主强调色 - 莫兰迪蓝
        'accent_green_dark': '#8ec5db',       # 深莫兰迪蓝
        'accent_green_light': '#bfe6f2',      # 浅莫兰迪蓝
        'accent_blue': '#a8d8ea',             # 辅助色 - 莫兰迪蓝
        'accent_yellow': '#FFD700',           # 警告黄色 (保持不变)
        'accent_red': '#FF6B6B',              # 错误红色 (保持不变)

        # 边框和分隔线
        'border_color': '#4a4a4a',            # 默认边框颜色
        'border_focus': '#a8d8ea',            # 焦点边框颜色
        'border_error': '#FF6B6B',            # 错误边框颜色
        'separator_color': '#333333',         # 分隔线颜色

        # 阴影和效果
        'shadow_color': '#000000',            # 阴影颜色
        'overlay_color': 'rgba(0, 0, 0, 0.5)',  # 遮罩颜色
        'glass_color': 'rgba(58, 58, 58, 0.8)',  # 毛玻璃颜色

        # 状态色系
        'success_color': '#a8d8ea',           # 成功状态色 - 莫兰迪蓝
        'warning_color': '#FFD700',           # 警告状态色
        'error_color': '#FF6B6B',             # 错误状态色
        'info_color': '#a8d8ea',              # 信息状态色 - 莫兰迪蓝
    }

    # 字体配置
    FONTS = {
        'primary': ('Segoe UI', 12),
        'heading': ('Segoe UI', 16, QtGui.QFont.Weight.Bold),
        'caption': ('Segoe UI', 10),
        'code': ('Consolas', 11)
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color_cache = {}
        self._font_cache = {}
        self._init_fonts()

    def _init_fonts(self):
        """初始化字体缓存"""
        for name, config in self.FONTS.items():
            if len(config) == 3:
                font = QtGui.QFont(config[0], config[1], config[2])
            else:
                font = QtGui.QFont(config[0], config[1])
            self._font_cache[name] = font

    def get_color(self, color_name: str) -> QtGui.QColor:
        """获取主题颜色"""
        if color_name not in self._color_cache:
            if color_name in self.COLORS:
                self._color_cache[color_name] = QtGui.QColor(
                    self.COLORS[color_name])
            else:
                # 默认返回白色
                self._color_cache[color_name] = QtGui.QColor('#FFFFFF')
        return self._color_cache[color_name]

    def get_font(self, font_name: str) -> QtGui.QFont:
        """获取主题字体"""
        return self._font_cache.get(font_name, self._font_cache['primary'])

    def ensure_contrast_ratio(self, fg_color: str, bg_color: str, min_ratio: float = 4.5) -> bool:
        """确保颜色对比度满足可访问性标准"""
        fg = QtGui.QColor(fg_color)
        bg = QtGui.QColor(bg_color)

        # 计算相对亮度
        def get_luminance(color: QtGui.QColor) -> float:
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0

            def gamma_correct(c):
                return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)

            r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        fg_lum = get_luminance(fg)
        bg_lum = get_luminance(bg)

        # 计算对比度
        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        contrast_ratio = (lighter + 0.05) / (darker + 0.05)

        return contrast_ratio >= min_ratio

    def apply_theme_to_widget(self, widget: QtWidgets.QWidget):
        """将暗色主题应用到指定组件"""
        widget_type = widget.__class__.__name__
        stylesheet = self.generate_stylesheet(widget_type)
        if stylesheet:
            widget.setStyleSheet(stylesheet)

    def generate_complete_stylesheet(self) -> str:
        """生成完整的应用程序样式表"""
        return f"""
            /* 全局样式 */
            QWidget {{
                background-color: {self.COLORS['background_primary']};
                color: {self.COLORS['text_primary']};
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 12px;
            }}

            /* 按钮样式 */
            QPushButton {{
                background-color: {self.COLORS['background_card']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {self.COLORS['accent_green_dark']};
                border-color: {self.COLORS['accent_green']};
                color: {self.COLORS['background_primary']};
            }}
            QPushButton:pressed {{
                background-color: {self.COLORS['accent_green']};
                color: {self.COLORS['background_primary']};
            }}
            QPushButton:disabled {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_disabled']};
                border-color: {self.COLORS['text_disabled']};
            }}

            /* 输入框样式 */
            QLineEdit {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_primary']};
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {self.COLORS['accent_green']};
                background-color: {self.COLORS['background_card']};
            }}
            QLineEdit:disabled {{
                background-color: {self.COLORS['background_primary']};
                color: {self.COLORS['text_disabled']};
                border-color: {self.COLORS['text_disabled']};
            }}

            /* 文本区域样式 */
            QTextEdit, QPlainTextEdit {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_primary']};
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {self.COLORS['accent_green']};
            }}

            /* 标签样式 */
            QLabel {{
                background-color: transparent;
                color: {self.COLORS['text_primary']};
                font-size: 12px;
            }}

            /* 框架样式 */
            QFrame {{
                background-color: {self.COLORS['background_card']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 8px;
            }}

            /* 分组框样式 */
            QGroupBox {{
                background-color: {self.COLORS['background_card']};
                color: {self.COLORS['text_primary']};
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: {self.COLORS['accent_green']};
            }}

            /* 滚动条样式 */
            QScrollBar:vertical {{
                background-color: {self.COLORS['background_secondary']};
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.COLORS['accent_green']};
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.COLORS['accent_green_light']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}

            QScrollBar:horizontal {{
                background-color: {self.COLORS['background_secondary']};
                height: 12px;
                border-radius: 6px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {self.COLORS['accent_green']};
                border-radius: 6px;
                min-width: 20px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.COLORS['accent_green_light']};
            }}

            /* 复选框样式 */
            QCheckBox {{
                color: {self.COLORS['text_primary']};
                font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 3px;
                background-color: {self.COLORS['background_secondary']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.COLORS['accent_green']};
                border-color: {self.COLORS['accent_green']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {self.COLORS['accent_green_light']};
            }}

            /* 单选按钮样式 */
            QRadioButton {{
                color: {self.COLORS['text_primary']};
                font-size: 12px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 8px;
                background-color: {self.COLORS['background_secondary']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {self.COLORS['accent_green']};
                border-color: {self.COLORS['accent_green']};
            }}

            /* 下拉框样式 */
            QComboBox {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_primary']};
                border: 2px solid {self.COLORS['border_color']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {self.COLORS['accent_green']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.COLORS['text_secondary']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.COLORS['background_card']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                selection-background-color: {self.COLORS['accent_green']};
                selection-color: {self.COLORS['background_primary']};
            }}

            /* 进度条样式 */
            QProgressBar {{
                background-color: {self.COLORS['background_secondary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 8px;
                text-align: center;
                color: {self.COLORS['text_primary']};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.COLORS['accent_green']}, 
                    stop:1 {self.COLORS['accent_green_light']});
                border-radius: 7px;
            }}

            /* 滑块样式 */
            QSlider::groove:horizontal {{
                background-color: {self.COLORS['background_secondary']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: {self.COLORS['accent_green']};
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {self.COLORS['accent_green_light']};
            }}

            /* 选项卡样式 */
            QTabWidget::pane {{
                background-color: {self.COLORS['background_card']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_secondary']};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {self.COLORS['accent_green']};
                color: {self.COLORS['background_primary']};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {self.COLORS['background_hover']};
                color: {self.COLORS['text_primary']};
            }}

            /* 菜单样式 */
            QMenuBar {{
                background-color: {self.COLORS['background_primary']};
                color: {self.COLORS['text_primary']};
                border-bottom: 1px solid {self.COLORS['border_color']};
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                background-color: transparent;
            }}
            QMenuBar::item:selected {{
                background-color: {self.COLORS['accent_green']};
                color: {self.COLORS['background_primary']};
            }}

            QMenu {{
                background-color: {self.COLORS['background_card']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['border_color']};
                border-radius: 6px;
            }}
            QMenu::item {{
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {self.COLORS['accent_green']};
                color: {self.COLORS['background_primary']};
            }}

            /* 工具提示样式 */
            QToolTip {{
                background-color: {self.COLORS['background_card']};
                color: {self.COLORS['text_primary']};
                border: 1px solid {self.COLORS['accent_green']};
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
            }}

            /* 状态栏样式 */
            QStatusBar {{
                background-color: {self.COLORS['background_secondary']};
                color: {self.COLORS['text_primary']};
                border-top: 1px solid {self.COLORS['border_color']};
            }}
        """

    def generate_stylesheet(self, widget_type: str) -> str:
        """生成指定组件类型的样式表"""
        base_style = f"""
            background-color: {self.COLORS['background_primary']};
            color: {self.COLORS['text_primary']};
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            border: none;
        """

        if widget_type == 'QPushButton':
            return f"""
                QPushButton {{
                    {base_style}
                    background-color: {self.COLORS['background_card']};
                    border: 1px solid {self.COLORS['border_color']};
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.COLORS['accent_green_dark']};
                    border-color: {self.COLORS['accent_green']};
                }}
                QPushButton:pressed {{
                    background-color: {self.COLORS['accent_green']};
                }}
            """
        elif widget_type == 'QLineEdit':
            return f"""
                QLineEdit {{
                    {base_style}
                    background-color: {self.COLORS['background_secondary']};
                    border: 2px solid {self.COLORS['border_color']};
                    border-radius: 6px;
                    padding: 6px;
                }}
                QLineEdit:focus {{
                    border-color: {self.COLORS['accent_green']};
                }}
            """
        elif widget_type == 'QFrame':
            return f"""
                QFrame {{
                    {base_style}
                    background-color: {self.COLORS['background_card']};
                    border-radius: 12px;
                }}
            """
        else:
            return base_style

    @classmethod
    def get_instance(cls) -> 'DarkThemeManager':
        """获取单例实例"""
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance
