"""
建议弹窗组件

提供精美的建议弹窗，包含任务建议、环境建议、行为建议等不同类型的内容。
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
from typing import Dict, List
from .dark_theme_manager import DarkThemeManager
from .precision_animation_engine import PrecisionAnimationEngine
from .visual_effects_manager import VisualEffectsManager
from .startup_particle_system import StartupParticleSystem
from .interaction_feedback_system import InteractionFeedbackSystem


class SuggestionDialog(QtWidgets.QDialog):
    """精美的建议弹窗 - 增强错误处理和调试功能"""

    # 信号
    creationFailed = Signal(str)  # 创建失败原因
    displayFailed = Signal(str)   # 显示失败原因

    # 建议内容数据 - 增强版本，包含丰富的视觉效果配置
    SUGGESTIONS = {
        "💡 效率高峰期": {
            "type": "任务建议",
            "icon": "🎯",
            "title": "高效时段优化建议",
            "visual_config": {
                "theme_color": "#a8d8ea",
                "background_gradient": ("#1a1a1a", "#2a3a40"),
                "icon_animation": "pulse",
                "entrance_effect": "elastic"
            },
            "suggestions": [
                {
                    "category": "🎯 核心任务安排",
                    "icon": "🎯",
                    "animation_delay": 0,
                    "items": [
                        "将最重要的编程任务安排在9-11点黄金时段",
                        "利用高峰期处理复杂的算法和架构设计",
                        "避免在高峰期处理邮件和琐碎事务",
                        "开启专注模式，屏蔽所有通知和干扰源"
                    ]
                },
                {
                    "category": "⏰ 时间管理技巧",
                    "icon": "⏰",
                    "animation_delay": 200,
                    "items": [
                        "使用番茄工作法：25分钟深度专注+5分钟放松",
                        "提前准备开发环境、文档和所需资料",
                        "为每个任务设定明确目标和完成标准",
                        "记录并分析个人高效时段的规律"
                    ]
                }
            ],
            "motivational": "✨ 抓住黄金时段，让每一分钟都闪闪发光！你的专注力就是通往成功的超能力！🎯💪"
        },
        "⚠️ 易分心时段": {
            "type": "环境建议",
            "icon": "🌿",
            "title": "专注环境优化方案",
            "visual_config": {
                "theme_color": "#a8d8ea",
                "background_gradient": ("#1a1a1a", "#2a3a40"),
                "icon_animation": "glow",
                "entrance_effect": "slide_up"
            },
            "suggestions": [
                {
                    "category": "🌿 环境优化",
                    "icon": "🌿",
                    "animation_delay": 0,
                    "items": [
                        "调节工作区光线，使用护眼的暖色调灯光",
                        "播放专注音乐：白噪音、自然声音或轻音乐",
                        "整理工作台面，营造简洁舒适的空间",
                        "准备健康零食和充足水分，保持身体状态"
                    ]
                },
                {
                    "category": "🧠 注意力管理",
                    "icon": "🧠",
                    "animation_delay": 200,
                    "items": [
                        "使用专业工具屏蔽娱乐网站和应用",
                        "将手机设为静音并放置在视线范围外",
                        "安排轻松任务：代码重构、文档整理等",
                        "每30分钟进行眼部放松和深呼吸练习"
                    ]
                }
            ],
            "motivational": "🌟 打造专属的专注圣地，让分心无处遁形！完美环境成就完美状态！🌿✨"
        },
        "📈 成长趋势": {
            "type": "行为建议",
            "icon": "🚀",
            "title": "持续成长行动计划",
            "visual_config": {
                "theme_color": "#a8d8ea",
                "background_gradient": ("#1a1a1a", "#2a3a40"),
                "icon_animation": "bounce",
                "entrance_effect": "scale_fade"
            },
            "suggestions": [
                {
                    "category": "🚀 技能进阶",
                    "icon": "🚀",
                    "animation_delay": 0,
                    "items": [
                        "每周掌握一个新的编程技巧或开发工具",
                        "积极参与开源项目，在实战中提升代码品质",
                        "定期进行代码审查和重构，追求代码艺术",
                        "建立技术博客，分享学习心得和项目经验"
                    ]
                },
                {
                    "category": "💎 习惯塑造",
                    "icon": "💎",
                    "animation_delay": 200,
                    "items": [
                        "坚持每日代码提交，保持编程的连续性",
                        "制定周目标和月目标，让成长看得见",
                        "建立规律作息，用充足睡眠为大脑充电",
                        "定期复盘总结，持续优化工作方法"
                    ]
                }
            ],
            "motivational": "🌟 你就是那颗最亮的成长之星！每一次小进步都在为未来的大突破蓄力！继续闪耀吧！🚀💫"
        }
    }

    def __init__(self, suggestion_key: str, parent=None):
        super().__init__(parent)
        self.suggestion_key = suggestion_key

        # 初始化日志记录
        import logging
        self.logger = logging.getLogger(f"{__name__}.SuggestionDialog")
        self.logger.setLevel(logging.DEBUG)

        # 创建控制台处理器（如果还没有）
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self.log_creation_process(
            "initialization", True, f"开始初始化建议弹窗，键: '{suggestion_key}'")

        # 验证建议数据
        if not self.validate_suggestion_data():
            self.handle_missing_suggestion_data(suggestion_key)
            return

        try:
            # 安全创建弹窗
            if not self.create_dialog_safely():
                return

        except Exception as e:
            error_msg = f"弹窗初始化失败: {str(e)}"
            self.logger.error(error_msg)
            self.creationFailed.emit(error_msg)
            raise

    def validate_suggestion_data(self) -> bool:
        """验证建议数据"""
        try:
            self.log_creation_process(
                "data_validation", True, f"验证建议数据，键: '{self.suggestion_key}'")

            # 检查键是否存在
            if self.suggestion_key not in self.SUGGESTIONS:
                available_keys = list(self.SUGGESTIONS.keys())
                self.log_creation_process("data_validation", False,
                                          f"无效的建议键: '{self.suggestion_key}', 可用键: {available_keys}")
                return False

            # 获取建议数据
            self.suggestion_data = self.SUGGESTIONS.get(
                self.suggestion_key, {})
            self.visual_config = self.suggestion_data.get("visual_config", {})

            # 验证必要字段
            required_fields = ['type', 'icon',
                               'title', 'suggestions', 'motivational']
            for field in required_fields:
                if field not in self.suggestion_data:
                    self.log_creation_process("data_validation", False,
                                              f"缺少必要字段: {field}")
                    return False

            # 验证建议内容
            suggestions = self.suggestion_data.get('suggestions', [])
            if not suggestions or len(suggestions) == 0:
                self.log_creation_process("data_validation", False, "建议内容为空")
                return False

            # 验证每个建议分类
            for i, suggestion_group in enumerate(suggestions):
                if not isinstance(suggestion_group, dict):
                    self.log_creation_process("data_validation", False,
                                              f"建议分组 {i} 格式错误")
                    return False

                items = suggestion_group.get('items', [])
                if not items or len(items) < 4:
                    self.log_creation_process("data_validation", False,
                                              f"建议分组 {i} 的建议数量不足（需要至少4条）")
                    return False

            self.log_creation_process("data_validation", True, "建议数据验证通过")
            return True

        except Exception as e:
            self.log_creation_process(
                "data_validation", False, f"验证过程出错: {str(e)}")
            return False

    def create_dialog_safely(self) -> bool:
        """安全创建弹窗"""
        try:
            self.log_creation_process("dialog_creation", True, "开始创建弹窗组件")

            # 初始化视觉增强组件
            self.theme_manager = DarkThemeManager.get_instance()
            self.animation_engine = PrecisionAnimationEngine(self)
            self.effects_manager = VisualEffectsManager(self)
            self.feedback_system = InteractionFeedbackSystem(self)

            # 设置弹窗属性
            self.setWindowFlags(
                QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setModal(True)
            self.setFixedSize(520, 650)

            # 创建粒子系统
            self.particle_system = StartupParticleSystem(self)
            self.particle_system.resize(self.size())

            # 动画相关属性
            self.content_items = []
            self.icon_animation_timer = QtCore.QTimer(self)
            self.icon_animation_timer.timeout.connect(self.animate_icon)

            # 设置UI
            self.setup_ui()

            # 应用视觉效果
            self.apply_visual_effects()

            # 居中显示
            self.center_on_parent()

            # 验证视觉组件
            if not self.validate_visual_components():
                return False

            self.log_creation_process("dialog_creation", True, "弹窗创建完成")
            return True

        except Exception as e:
            self.log_creation_process(
                "dialog_creation", False, f"创建失败: {str(e)}")
            self.creationFailed.emit(str(e))
            return False

    def show_with_error_handling(self) -> bool:
        """带错误处理的显示方法"""
        try:
            self.log_creation_process("display", True, "开始显示弹窗")

            # 确保弹窗正确定位
            if not self.ensure_proper_positioning():
                return False

            # 显示弹窗
            self.show_with_animation()

            # 验证显示结果
            if not self.isVisible():
                error_msg = "弹窗显示后不可见"
                self.log_creation_process("display", False, error_msg)
                self.displayFailed.emit(error_msg)
                return False

            self.log_creation_process("display", True, "弹窗显示成功")
            return True

        except Exception as e:
            error_msg = f"显示弹窗失败: {str(e)}"
            self.log_creation_process("display", False, error_msg)
            self.displayFailed.emit(error_msg)
            return False

    def log_creation_process(self, step: str, success: bool, details: str = ""):
        """记录创建过程"""
        status = "SUCCESS" if success else "FAILED"
        log_message = f"[{step.upper()}] {status}: {details}"

        if success:
            self.logger.info(log_message)
        else:
            self.logger.error(log_message)

        # 同时输出到控制台以便调试
        print(f"SuggestionDialog: {log_message}")

    def handle_missing_suggestion_data(self, key: str):
        """处理缺少建议数据的情况"""
        available_keys = list(self.SUGGESTIONS.keys())
        error_msg = f"找不到建议数据，键: '{key}', 可用键: {available_keys}"

        self.log_creation_process("missing_data", False, error_msg)
        self.creationFailed.emit(error_msg)

        # 输出详细调试信息
        print(f"=== 建议数据缺失详细信息 ===")
        print(f"请求的键: '{key}'")
        print(f"键的类型: {type(key)}")
        print(f"键的长度: {len(key) if isinstance(key, str) else 'N/A'}")
        print(f"可用的键: {available_keys}")
        print(f"键匹配检查:")
        for available_key in available_keys:
            print(f"  '{available_key}' == '{key}': {available_key == key}")
            print(f"  '{available_key}' 长度: {len(available_key)}")
        print(f"=== 调试信息结束 ===")

    def ensure_proper_positioning(self) -> bool:
        """确保弹窗正确定位"""
        try:
            # 获取屏幕信息
            screen = QtWidgets.QApplication.primaryScreen()
            if not screen:
                self.logger.warning("无法获取主屏幕信息")
                return True  # 继续尝试显示

            screen_geometry = screen.geometry()
            dialog_geometry = self.geometry()

            # 检查弹窗是否在屏幕范围内
            if not screen_geometry.contains(dialog_geometry):
                # 重新定位到屏幕中央
                center_x = screen_geometry.center().x() - dialog_geometry.width() // 2
                center_y = screen_geometry.center().y() - dialog_geometry.height() // 2
                self.move(center_x, center_y)

                self.logger.info(f"弹窗重新定位到: ({center_x}, {center_y})")

            return True

        except Exception as e:
            self.logger.error(f"定位弹窗失败: {str(e)}")
            return False

    def validate_visual_components(self) -> bool:
        """验证视觉组件"""
        try:
            # 检查必要的组件是否存在
            required_components = [
                'theme_manager', 'animation_engine', 'effects_manager',
                'feedback_system', 'particle_system'
            ]

            for component in required_components:
                if not hasattr(self, component) or getattr(self, component) is None:
                    self.log_creation_process("component_validation", False,
                                              f"缺少组件: {component}")
                    return False

            # 检查弹窗几何属性
            geometry = self.geometry()
            if geometry.width() <= 0 or geometry.height() <= 0:
                self.log_creation_process("component_validation", False,
                                          f"弹窗几何属性无效: {geometry}")
                return False

            self.log_creation_process("component_validation", True, "视觉组件验证通过")
            return True

        except Exception as e:
            self.log_creation_process(
                "component_validation", False, f"验证失败: {str(e)}")
            return False

    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # 标题区域
        self.create_header(main_layout)

        # 内容区域
        self.create_content(main_layout)

        # 底部按钮
        self.create_footer(main_layout)

    def create_header(self, layout):
        """创建标题区域"""
        header_layout = QtWidgets.QHBoxLayout()

        # 图标 - 支持动画效果
        self.icon_label = QtWidgets.QLabel(
            self.suggestion_data.get("icon", "💡"))
        theme_color = self.visual_config.get(
            "theme_color", self.theme_manager.COLORS['accent_green'])
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 36px;
                color: {theme_color};
                background: transparent;
            }}
        """)
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setFixedSize(60, 60)

        # 标题和类型
        title_layout = QtWidgets.QVBoxLayout()

        # 建议类型
        type_label = QtWidgets.QLabel(self.suggestion_data.get("type", "建议"))
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {theme_color};
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }}
        """)

        # 主标题
        title_label = QtWidgets.QLabel(
            self.suggestion_data.get("title", "建议详情"))
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_manager.COLORS['text_primary']};
                font-size: 19px;
                font-weight: bold;
                background: transparent;
            }}
        """)

        title_layout.addWidget(type_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 关闭按钮
        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme_manager.COLORS['text_secondary']};
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-radius: 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme_manager.COLORS.get('error_color', '#FF4444')};
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.close_with_animation)

        header_layout.addWidget(self.icon_label)
        header_layout.addLayout(title_layout)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

    def create_content(self, layout):
        """创建内容区域"""
        # 滚动区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.theme_manager.COLORS['background_secondary']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.theme_manager.COLORS['accent_green']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.theme_manager.COLORS['accent_green_light']};
            }}
        """)

        # 内容容器 - 设置暗色背景
        content_widget = QtWidgets.QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme_manager.COLORS['background_primary']};
                color: {self.theme_manager.COLORS['text_primary']};
            }}
        """)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        # 添加建议内容
        suggestions = self.suggestion_data.get("suggestions", [])
        for suggestion_group in suggestions:
            self.create_suggestion_group(content_layout, suggestion_group)

        # 添加激励话语
        motivational_message = self.suggestion_data.get("motivational", "")
        if motivational_message:
            self.create_motivational_section(
                content_layout, motivational_message)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def create_suggestion_group(self, layout, group_data):
        """创建建议组"""
        theme_color = self.visual_config.get(
            "theme_color", self.theme_manager.COLORS['accent_green'])

        # 分组标题容器
        category_container = QtWidgets.QWidget()
        category_container.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {self.theme_manager.COLORS['text_primary']};
            }}
        """)
        category_layout = QtWidgets.QHBoxLayout(category_container)
        category_layout.setContentsMargins(0, 8, 0, 8)

        # 分组图标
        category_icon = QtWidgets.QLabel(group_data.get("icon", "📝"))
        category_icon.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                background: transparent;
            }}
        """)

        # 分组标题
        category_label = QtWidgets.QLabel(group_data.get("category", "建议"))
        category_label.setStyleSheet(f"""
            QLabel {{
                color: {theme_color};
                font-size: 15px;
                font-weight: bold;
                background: transparent;
            }}
        """)

        category_layout.addWidget(category_icon)
        category_layout.addWidget(category_label)
        category_layout.addStretch()

        # 设置初始透明度为0，用于动画
        category_container.setWindowOpacity(0)
        self.content_items.append(category_container)

        layout.addWidget(category_container)

        # 建议项目
        items = group_data.get("items", [])
        for i, item in enumerate(items):
            item_widget = self.create_suggestion_item(item, i)
            # 设置初始透明度为0，用于动画
            item_widget.setWindowOpacity(0)
            self.content_items.append(item_widget)
            layout.addWidget(item_widget)

        # 分隔线
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme_manager.COLORS.get('separator_color', '#4a4a4a')};
                border: none;
                height: 1px;
                margin: 15px 0px;
            }}
        """)
        layout.addWidget(separator)

    def create_suggestion_item(self, text: str, index: int):
        """创建单个建议项"""
        item_widget = QtWidgets.QWidget()
        item_widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {self.theme_manager.COLORS['text_primary']};
            }}
        """)
        item_layout = QtWidgets.QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 5, 0, 5)

        # 序号圆点
        number_label = QtWidgets.QLabel(str(index + 1))
        number_label.setFixedSize(24, 24)
        number_label.setAlignment(QtCore.Qt.AlignCenter)
        number_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.theme_manager.COLORS['accent_green']};
                color: {self.theme_manager.COLORS['background_primary']};
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

        # 建议文本
        text_label = QtWidgets.QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_manager.COLORS['text_primary']};
                font-size: 12px;
                line-height: 1.4;
                padding: 2px 8px;
                background: transparent;
            }}
        """)

        item_layout.addWidget(number_label)
        item_layout.addWidget(text_label)
        item_layout.addStretch()

        return item_widget

    def create_motivational_section(self, layout, message):
        """创建激励话语部分"""
        theme_color = self.visual_config.get(
            "theme_color", self.theme_manager.COLORS['accent_green'])

        # 激励话语容器 - 完全暗色主题，无边框
        motivational_container = QtWidgets.QWidget()
        motivational_container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {self.theme_manager.COLORS['background_secondary']}, 
                    stop:1 {self.theme_manager.COLORS['background_card']});
                border-radius: 15px;
                border: none;
                margin: 10px 0px;
            }}
        """)

        motivational_layout = QtWidgets.QVBoxLayout(motivational_container)
        motivational_layout.setContentsMargins(20, 15, 20, 15)

        # 激励标题
        motivational_title = QtWidgets.QLabel("💫 激励时刻")
        motivational_title.setStyleSheet(f"""
            QLabel {{
                color: {theme_color};
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        motivational_layout.addWidget(motivational_title)

        # 激励内容
        motivational_text = QtWidgets.QLabel(message)
        motivational_text.setWordWrap(True)
        motivational_text.setStyleSheet(f"""
            QLabel {{
                color: {self.theme_manager.COLORS['text_primary']};
                font-size: 13px;
                line-height: 1.5;
                background: transparent;
                padding: 5px 0px;
            }}
        """)
        motivational_layout.addWidget(motivational_text)

        # 设置初始透明度为0，用于动画
        motivational_container.setWindowOpacity(0)
        self.content_items.append(motivational_container)

        layout.addWidget(motivational_container)

    def animate_icon(self):
        """图标动画效果"""
        if not hasattr(self, 'icon_label'):
            return

        animation_type = self.visual_config.get("icon_animation", "pulse")

        if animation_type == "pulse":
            # 脉冲效果
            self.icon_pulse_animation = QtCore.QPropertyAnimation(
                self.icon_label, b"geometry")
            current_geo = self.icon_label.geometry()
            expanded_geo = QtCore.QRect(
                current_geo.x() - 3, current_geo.y() - 3,
                current_geo.width() + 6, current_geo.height() + 6
            )

            self.icon_pulse_animation.setDuration(800)
            self.icon_pulse_animation.setStartValue(current_geo)
            self.icon_pulse_animation.setKeyValueAt(0.5, expanded_geo)
            self.icon_pulse_animation.setEndValue(current_geo)
            self.icon_pulse_animation.setEasingCurve(
                QtCore.QEasingCurve.InOutQuad)
            self.icon_pulse_animation.start()

        elif animation_type == "bounce":
            # 弹跳效果
            self.icon_bounce_animation = QtCore.QPropertyAnimation(
                self.icon_label, b"geometry")
            current_geo = self.icon_label.geometry()
            bounce_geo = QtCore.QRect(
                current_geo.x(), current_geo.y() - 8,
                current_geo.width(), current_geo.height()
            )

            self.icon_bounce_animation.setDuration(600)
            self.icon_bounce_animation.setStartValue(current_geo)
            self.icon_bounce_animation.setKeyValueAt(0.3, bounce_geo)
            self.icon_bounce_animation.setEndValue(current_geo)
            self.icon_bounce_animation.setEasingCurve(
                QtCore.QEasingCurve.OutBounce)
            self.icon_bounce_animation.start()

    def start_content_animations(self):
        """启动内容分层动画"""
        for i, item in enumerate(self.content_items):
            # 为每个项目创建淡入动画
            opacity_effect = QtWidgets.QGraphicsOpacityEffect()
            item.setGraphicsEffect(opacity_effect)

            animation = QtCore.QPropertyAnimation(opacity_effect, b"opacity")
            animation.setDuration(400)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QtCore.QEasingCurve.OutQuad)

            # 延迟启动，创建分层效果
            QtCore.QTimer.singleShot(i * 80, animation.start)

    def create_background_blur_effect(self):
        """创建背景模糊效果"""
        if self.parent():
            # 为父窗口添加模糊效果
            blur_effect = QtWidgets.QGraphicsBlurEffect()
            blur_effect.setBlurRadius(10)
            self.parent().setGraphicsEffect(blur_effect)

            # 保存原始效果以便恢复
            self.original_parent_effect = self.parent().graphicsEffect()

    def remove_background_blur_effect(self):
        """移除背景模糊效果"""
        if self.parent() and hasattr(self, 'original_parent_effect'):
            self.parent().setGraphicsEffect(None)

    def cleanup_and_close(self):
        """清理资源并关闭弹窗"""
        # 停止图标动画定时器
        if hasattr(self, 'icon_animation_timer'):
            self.icon_animation_timer.stop()

        # 清理弹窗顶层粒子系统
        if hasattr(self, 'dialog_particle_system'):
            self.dialog_particle_system._complete_effect()
            self.dialog_particle_system.deleteLater()
            delattr(self, 'dialog_particle_system')

        # 移除背景模糊效果
        self.remove_background_blur_effect()

        # 关闭弹窗
        # 使用 accept() 而不是 close()，因为这是 Dialog
        self.accept()

    def create_footer(self, layout):
        """创建底部按钮区域"""
        footer_layout = QtWidgets.QHBoxLayout()
        theme_color = self.visual_config.get(
            "theme_color", self.theme_manager.COLORS['accent_green'])

        # 应用建议按钮 - 暗色主题优化
        self.apply_btn = QtWidgets.QPushButton("📌 应用这些建议")
        self.apply_btn.setFixedHeight(45)
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_color}, 
                    stop:1 {theme_color}CC);
                color: {self.theme_manager.COLORS['background_primary']};
                border: none;
                border-radius: 22px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px 25px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {theme_color}EE, 
                    stop:1 {theme_color});
                color: {self.theme_manager.COLORS['background_primary']};
            }}
            QPushButton:pressed {{
                background: {theme_color}AA;
                color: {self.theme_manager.COLORS['background_primary']};
            }}
        """)

        # 为按钮添加悬停和点击反馈
        self.effects_manager.apply_button_gradient(
            self.apply_btn, [theme_color, f"{theme_color}CC"])
        self.feedback_system.setup_hover_feedback(
            self.apply_btn, scale_factor=1.02)
        self.feedback_system.setup_click_feedback(
            self.apply_btn, with_particles=True)
        self.apply_btn.clicked.connect(self.apply_suggestions)

        # 稍后提醒按钮 - 暗色主题优化
        self.remind_btn = QtWidgets.QPushButton("⏰ 稍后提醒")
        self.remind_btn.setFixedHeight(45)
        self.remind_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme_manager.COLORS['background_secondary']};
                color: {self.theme_manager.COLORS['text_primary']};
                border: 2px solid {theme_color}60;
                border-radius: 22px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px 25px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {theme_color}20;
                border-color: {theme_color};
                color: {self.theme_manager.COLORS['text_primary']};
            }}
            QPushButton:pressed {{
                background-color: {theme_color}40;
                color: {self.theme_manager.COLORS['text_primary']};
            }}
        """)

        # 为按钮添加悬停和点击反馈
        self.feedback_system.setup_hover_feedback(
            self.remind_btn, scale_factor=1.02)
        self.feedback_system.setup_click_feedback(
            self.remind_btn, with_particles=False)
        self.remind_btn.clicked.connect(self.remind_later)

        footer_layout.addWidget(self.apply_btn)
        footer_layout.addWidget(self.remind_btn)

        layout.addLayout(footer_layout)

    def apply_visual_effects(self):
        """应用视觉效果"""
        # 应用阴影效果
        self.effects_manager.apply_card_shadow(
            self, blur_radius=30, offset=(0, 10), opacity=0.5)

    def center_on_parent(self):
        """在父窗口中居中显示"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            # 在屏幕中央显示
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def show_with_animation(self):
        """带动画效果显示弹窗"""
        entrance_effect = self.visual_config.get("entrance_effect", "elastic")

        # 初始状态：缩小和透明
        self.setWindowOpacity(0)
        original_size = self.size()

        if entrance_effect == "elastic":
            self.resize(int(original_size.width() * 0.7),
                        int(original_size.height() * 0.7))
            easing = QtCore.QEasingCurve.OutElastic
        elif entrance_effect == "slide_up":
            # 从下方滑入
            original_pos = self.pos()
            self.move(original_pos.x(), original_pos.y() + 100)
            easing = QtCore.QEasingCurve.OutCubic
        else:  # scale_fade
            self.resize(int(original_size.width() * 0.8),
                        int(original_size.height() * 0.8))
            easing = QtCore.QEasingCurve.OutBack

        # 显示弹窗
        self.show()

        # 创建背景模糊效果
        self.create_background_blur_effect()

        # 触发弹窗内部粒子庆祝效果
        center = QtCore.QPoint(self.width() // 2, self.height() // 2)
        self.particle_system.trigger_startup_effect(center)

        # 🎉 触发弹窗顶层粒子庆祝效果
        self.trigger_dialog_celebration_particles()

        # 创建入场动画
        if entrance_effect == "slide_up":
            # 位置动画
            self.position_animation = QtCore.QPropertyAnimation(self, b"pos")
            self.position_animation.setDuration(500)
            self.position_animation.setStartValue(self.pos())
            self.position_animation.setEndValue(original_pos)
            self.position_animation.setEasingCurve(easing)
            self.position_animation.start()
        else:
            # 缩放动画
            self.scale_animation = QtCore.QPropertyAnimation(self, b"size")
            self.scale_animation.setDuration(600)
            self.scale_animation.setStartValue(self.size())
            self.scale_animation.setEndValue(original_size)
            self.scale_animation.setEasingCurve(easing)
            self.scale_animation.start()

        # 创建透明度动画
        self.opacity_animation = QtCore.QPropertyAnimation(
            self, b"windowOpacity")
        self.opacity_animation.setDuration(400)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        self.opacity_animation.start()

        # 启动内容分层动画
        QtCore.QTimer.singleShot(300, self.start_content_animations)

        # 启动图标动画
        self.icon_animation_timer.start(2000)  # 每2秒执行一次图标动画

    def close_with_animation(self):
        """带动画效果关闭弹窗"""
        # 防止重复调用
        if getattr(self, '_is_closing', False):
            return
        self._is_closing = True

        # 创建缩小动画
        self.close_scale_animation = QtCore.QPropertyAnimation(self, b"size")
        self.close_scale_animation.setDuration(250)
        self.close_scale_animation.setStartValue(self.size())
        end_size = QtCore.QSize(int(self.width() * 0.8),
                                int(self.height() * 0.8))
        self.close_scale_animation.setEndValue(end_size)
        self.close_scale_animation.setEasingCurve(QtCore.QEasingCurve.InBack)

        # 创建透明度动画
        self.close_opacity_animation = QtCore.QPropertyAnimation(
            self, b"windowOpacity")
        self.close_opacity_animation.setDuration(200)
        self.close_opacity_animation.setStartValue(1.0)
        self.close_opacity_animation.setEndValue(0.0)
        self.close_opacity_animation.setEasingCurve(QtCore.QEasingCurve.InQuad)

        # 动画完成后关闭
        self.close_opacity_animation.finished.connect(self.cleanup_and_close)

        # 启动动画
        self.close_scale_animation.start()
        self.close_opacity_animation.start()
        
        # 安全网：确保必定关闭
        QtCore.QTimer.singleShot(300, self.cleanup_and_close)

    def apply_suggestions(self):
        """应用建议"""
        # 显示成功反馈动画
        self.feedback_system.show_success_feedback(self.apply_btn, "建议已应用！")

        # 创建成功提示弹窗
        success_msg = QtWidgets.QMessageBox(self)
        success_msg.setWindowTitle("✅ 建议已应用")
        success_msg.setText(
            f"太棒了！已将{self.suggestion_data.get('type', '建议')}添加到您的行动计划中！")
        success_msg.setInformativeText("系统将在合适的时间提醒您执行这些建议，让我们一起变得更优秀！🚀")
        success_msg.setIcon(QtWidgets.QMessageBox.Information)

        # 应用暗色主题到消息框
        success_msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.theme_manager.COLORS['background_card']};
                color: {self.theme_manager.COLORS['text_primary']};
                border: 2px solid {self.visual_config.get('theme_color', '#a8d8ea')};
                border-radius: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QMessageBox QLabel {{
                color: {self.theme_manager.COLORS['text_primary']};
                background-color: transparent;
                font-size: 13px;
            }}
            QMessageBox QPushButton {{
                background-color: {self.visual_config.get('theme_color', '#a8d8ea')};
                color: {self.theme_manager.COLORS['background_primary']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self.visual_config.get('theme_color', '#a8d8ea')}EE;
            }}
        """)

        success_msg.exec()
        self.close_with_animation()

    def remind_later(self):
        """稍后提醒"""
        # 显示提醒反馈动画
        self.feedback_system.show_success_feedback(self.remind_btn, "提醒已设置！")

        # 创建提醒设置弹窗
        remind_msg = QtWidgets.QMessageBox(self)
        remind_msg.setWindowTitle("⏰ 提醒已设置")
        remind_msg.setText("好的！我们稍后再聊这些建议。")
        remind_msg.setInformativeText(
            "系统将在1小时后再次温馨提醒您查看这些建议。记住，每一个小改变都能带来大不同！💫")
        remind_msg.setIcon(QtWidgets.QMessageBox.Information)

        # 应用暗色主题到消息框
        remind_msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.theme_manager.COLORS['background_card']};
                color: {self.theme_manager.COLORS['text_primary']};
                border: 2px solid {self.visual_config.get('theme_color', '#a8d8ea')};
                border-radius: 12px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QMessageBox QLabel {{
                color: {self.theme_manager.COLORS['text_primary']};
                background-color: transparent;
                font-size: 13px;
            }}
            QMessageBox QPushButton {{
                background-color: {self.visual_config.get('theme_color', '#a8d8ea')};
                color: {self.theme_manager.COLORS['background_primary']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self.visual_config.get('theme_color', '#a8d8ea')}EE;
            }}
        """)

        remind_msg.exec()
        self.close_with_animation()

    def paintEvent(self, event):
        """绘制弹窗背景 - 暗色主题"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # 使用暗色主题背景
        theme_color = self.visual_config.get("theme_color",
                                             self.theme_manager.COLORS['accent_green'])

        # 绘制深色渐变背景
        gradient = QtGui.QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QtGui.QColor(
            self.theme_manager.COLORS['background_primary']))  # 深黑色
        gradient.setColorAt(0.5, QtGui.QColor(
            self.theme_manager.COLORS['background_secondary']))  # 中等灰色
        gradient.setColorAt(1, QtGui.QColor(
            self.theme_manager.COLORS['background_card']))  # 卡片灰色

        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 25, 25)

        # 绘制绿色发光边框
        border_color = QtGui.QColor(theme_color)
        border_color.setAlphaF(0.6)
        painter.setPen(QtGui.QPen(border_color, 3))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 25, 25)

        # 添加内部高光效果
        inner_highlight = QtGui.QColor(theme_color)
        inner_highlight.setAlphaF(0.15)
        painter.setPen(QtGui.QPen(inner_highlight, 1))
        painter.drawRoundedRect(self.rect().adjusted(3, 3, -3, -3), 22, 22)

    def trigger_dialog_celebration_particles(self):
        """触发弹窗顶层粒子庆祝效果 🎉"""
        try:
            self.log_creation_process("dialog_particles", True, "触发弹窗顶层粒子效果")

            # 创建弹窗顶层粒子系统
            if not hasattr(self, 'dialog_particle_system'):
                self.dialog_particle_system = StartupParticleSystem(self)
                self.dialog_particle_system.resize(self.size())
                
                # 再次确保鼠标穿透
                self.dialog_particle_system.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

                # 设置粒子系统在弹窗顶层
                self.dialog_particle_system.raise_()
                self.dialog_particle_system.show()

            # 计算弹窗顶部中心位置（标题区域）
            header_center = QtCore.QPoint(self.width() // 2, 80)

            # 触发庆祝粒子效果
            self.dialog_particle_system.trigger_startup_effect(header_center)

            self.log_creation_process(
                "dialog_particles", True, f"弹窗顶层粒子效果已触发，位置: {header_center}")

            # 延迟触发第二波粒子效果（从弹窗四角）
            QtCore.QTimer.singleShot(200, self.trigger_corner_particles)

        except Exception as e:
            error_msg = f"触发弹窗顶层粒子效果失败: {str(e)}"
            self.log_creation_process("dialog_particles", False, error_msg)
            # 粒子效果失败不应该影响主要功能

    def trigger_corner_particles(self):
        """触发弹窗四角粒子效果"""
        try:
            if hasattr(self, 'dialog_particle_system'):
                # 四个角的位置
                corners = [
                    QtCore.QPoint(50, 50),                           # 左上角
                    QtCore.QPoint(self.width() - 50, 50),           # 右上角
                    QtCore.QPoint(50, self.height() - 50),          # 左下角
                    QtCore.QPoint(self.width() - 50, self.height() - 50)  # 右下角
                ]

                # 依次触发四角粒子效果
                for i, corner in enumerate(corners):
                    QtCore.QTimer.singleShot(
                        i * 100, lambda pos=corner: self.trigger_single_corner_particle(pos))

        except Exception as e:
            self.log_creation_process(
                "corner_particles", False, f"触发四角粒子效果失败: {str(e)}")

    def trigger_single_corner_particle(self, position: QtCore.QPoint):
        """触发单个角落的粒子效果"""
        try:
            if hasattr(self, 'dialog_particle_system'):
                # 创建小规模的粒子爆炸
                self.dialog_particle_system.create_particle_burst(
                    position, 15)  # 较少的粒子数量

        except Exception as e:
            self.log_creation_process(
                "single_corner_particle", False, f"触发单角粒子效果失败: {str(e)}")

    def resizeEvent(self, event):
        """窗口大小改变时调整粒子系统"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_system'):
            self.particle_system.resize(self.size())
        if hasattr(self, 'dialog_particle_system'):
            self.dialog_particle_system.resize(self.size())
