"""
洞察卡片交互管理器

专门处理洞察卡片的点击事件和建议弹窗触发，提供详细的错误处理和调试功能。
"""

from PySide6 import QtCore, QtGui, QtWidgets
from typing import Dict, Optional
import traceback
import logging

from .dark_theme_manager import DarkThemeManager
from .precision_animation_engine import PrecisionAnimationEngine
from .suggestion_dialog import SuggestionDialog
from .startup_particle_system import StartupParticleSystem


class InsightCardInteractionManager(QtCore.QObject):
    """洞察卡片交互管理器 - 专门处理卡片点击事件和弹窗触发"""

    # 卡片标题到建议类型的映射
    CARD_SUGGESTION_MAPPING = {
        "💡 效率高峰期": "task_optimization",
        "⚠️ 易分心时段": "environment_improvement",
        "📈 成长趋势": "behavior_enhancement"
    }

    # 信号
    cardClicked = QtCore.Signal(str)  # 卡片标题
    dialogRequested = QtCore.Signal(str)  # 建议类型
    interactionError = QtCore.Signal(str, str)  # 错误类型, 错误消息

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化组件
        self.theme_manager = DarkThemeManager.get_instance()
        self.animation_engine = PrecisionAnimationEngine(self)

        # 初始化粒子系统（延迟创建，需要父窗口）
        self.particle_system = None

        # 设置日志记录
        self.logger = logging.getLogger(__name__)
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

        self.logger.info("InsightCardInteractionManager 初始化完成")

    def setup_card_interaction(self, card_widget: QtWidgets.QWidget, card_title: str):
        """为卡片设置交互功能"""
        try:
            self.log_interaction_event(
                "setup_interaction", f"设置卡片交互: {card_title}")

            # 验证卡片标题
            if not self.validate_card_title(card_title):
                error_msg = f"无效的卡片标题: {card_title}"
                self.logger.error(error_msg)
                self.interactionError.emit("invalid_title", error_msg)
                return False

            # 存储卡片信息
            card_widget.setProperty("card_title", card_title)

            # 连接点击事件
            if hasattr(card_widget, 'clicked'):
                card_widget.clicked.connect(
                    lambda: self.handle_card_click(card_title)
                )

            self.logger.info(f"卡片交互设置成功: {card_title}")
            return True

        except Exception as e:
            error_msg = f"设置卡片交互失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.interactionError.emit("setup_failed", error_msg)
            return False

    def handle_card_click(self, card_title: str, card_widget: QtWidgets.QWidget = None) -> bool:
        """处理卡片点击事件"""
        try:
            self.log_interaction_event("card_click", f"卡片被点击: {card_title}")
            self.cardClicked.emit(card_title)

            # 验证卡片标题
            if not self.validate_card_title(card_title):
                error_msg = f"点击了无效的卡片: {card_title}"
                self.logger.error(error_msg)
                self.interactionError.emit("invalid_click", error_msg)
                return False

            # 触发粒子庆祝效果 🎉
            if card_widget:
                self.trigger_celebration_particles(card_widget)

            # 显示建议弹窗
            success = self.show_suggestion_dialog(card_title)

            if success:
                self.log_interaction_event(
                    "dialog_shown", f"弹窗显示成功: {card_title}")
                suggestion_type = self.CARD_SUGGESTION_MAPPING.get(
                    card_title, "unknown")
                self.dialogRequested.emit(suggestion_type)
            else:
                self.log_interaction_event(
                    "dialog_failed", f"弹窗显示失败: {card_title}")

            return success

        except Exception as e:
            error_msg = f"处理卡片点击失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.interactionError.emit("click_failed", error_msg)
            return False

    def trigger_click_animation(self, card_widget: QtWidgets.QWidget) -> Optional[QtCore.QPropertyAnimation]:
        """触发卡片点击动画"""
        try:
            self.log_interaction_event("animation_start", "开始点击动画")

            # 创建点击动画
            animation = self.animation_engine.create_button_press_animation(
                card_widget)

            if animation:
                animation.start()
                self.logger.info("点击动画启动成功")
                return animation
            else:
                self.logger.warning("无法创建点击动画")
                return None

        except Exception as e:
            error_msg = f"触发点击动画失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.interactionError.emit("animation_failed", error_msg)
            return None

    def show_suggestion_dialog(self, card_title: str) -> bool:
        """显示建议弹窗"""
        try:
            self.log_interaction_event(
                "dialog_create", f"创建建议弹窗: {card_title}")

            # 验证卡片标题
            if not self.validate_card_title(card_title):
                error_msg = f"无法为无效卡片创建弹窗: {card_title}"
                self.logger.error(error_msg)
                self.interactionError.emit("invalid_dialog_request", error_msg)
                return False

            # 获取父窗口
            parent_widget = self.parent()
            if isinstance(parent_widget, QtWidgets.QWidget):
                # 寻找顶级窗口
                while parent_widget.parent():
                    parent_widget = parent_widget.parent()
            else:
                parent_widget = None

            # 创建建议弹窗
            dialog = SuggestionDialog(card_title, parent_widget)

            # 验证弹窗创建
            if not dialog:
                error_msg = f"弹窗创建失败: {card_title}"
                self.logger.error(error_msg)
                self.interactionError.emit("dialog_creation_failed", error_msg)
                return False

            # 验证建议数据
            if not dialog.suggestion_data:
                error_msg = f"弹窗缺少建议数据: {card_title}"
                self.logger.error(error_msg)
                self.handle_missing_suggestion_data(card_title)
                return False

            # 显示弹窗
            dialog.show_with_animation()

            # 验证弹窗可见性
            if not self.ensure_dialog_visibility(dialog):
                error_msg = f"弹窗显示后不可见: {card_title}"
                self.logger.error(error_msg)
                self.interactionError.emit("dialog_not_visible", error_msg)
                return False

            self.logger.info(f"建议弹窗显示成功: {card_title}")
            return True

        except Exception as e:
            error_msg = f"显示建议弹窗失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            self.handle_dialog_creation_error(e, card_title)
            return False

    def validate_card_title(self, title: str) -> bool:
        """验证卡片标题是否有效"""
        if not title or not isinstance(title, str):
            return False

        return title.strip() in self.CARD_SUGGESTION_MAPPING

    def log_interaction_event(self, event_type: str, details: str):
        """记录交互事件"""
        log_message = f"[{event_type.upper()}] {details}"
        self.logger.info(log_message)

        # 同时输出到控制台以便调试
        print(f"InsightCardInteractionManager: {log_message}")

    def handle_dialog_creation_error(self, error: Exception, card_title: str):
        """处理弹窗创建错误"""
        error_details = {
            'card_title': card_title,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }

        self.logger.error(f"弹窗创建错误详情: {error_details}")

        # 发出错误信号
        self.interactionError.emit("dialog_creation_error", str(error))

        # 输出详细调试信息
        print(f"=== 弹窗创建错误调试信息 ===")
        print(f"卡片标题: {card_title}")
        print(f"错误类型: {type(error).__name__}")
        print(f"错误消息: {str(error)}")
        print(f"完整堆栈跟踪:")
        print(traceback.format_exc())
        print(f"=== 错误调试信息结束 ===")

    def handle_missing_suggestion_data(self, card_title: str):
        """处理缺少建议数据的情况"""
        self.logger.error(f"卡片 '{card_title}' 缺少建议数据")

        available_keys = list(self.CARD_SUGGESTION_MAPPING.keys())
        self.logger.info(f"可用的卡片标题: {available_keys}")

        # 输出调试信息
        print(f"=== 建议数据缺失调试信息 ===")
        print(f"请求的卡片标题: '{card_title}'")
        print(f"可用的卡片标题: {available_keys}")
        print(f"标题映射: {self.CARD_SUGGESTION_MAPPING}")
        print(f"=== 调试信息结束 ===")

        self.interactionError.emit("missing_suggestion_data", card_title)

    def ensure_dialog_visibility(self, dialog: QtWidgets.QDialog) -> bool:
        """确保弹窗正确显示"""
        try:
            # 检查弹窗是否可见
            if not dialog.isVisible():
                self.logger.warning("弹窗创建后不可见，尝试强制显示")
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()

            # 检查弹窗几何属性
            geometry = dialog.geometry()
            if geometry.width() <= 0 or geometry.height() <= 0:
                self.logger.warning(f"弹窗几何属性异常: {geometry}")
                return False

            # 检查弹窗是否在屏幕范围内
            screen = QtWidgets.QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.geometry()
                if not screen_geometry.intersects(geometry):
                    self.logger.warning("弹窗不在屏幕范围内，重新定位")
                    dialog.move(screen_geometry.center() - geometry.center())

            self.logger.info(f"弹窗可见性验证通过: {geometry}")
            return True

        except Exception as e:
            self.logger.error(f"验证弹窗可见性失败: {str(e)}")
            return False

    def ensure_particle_system(self, parent_widget: QtWidgets.QWidget):
        """确保粒子系统已初始化"""
        if self.particle_system is None and parent_widget:
            # 寻找顶级窗口作为粒子系统的父窗口
            top_level_widget = parent_widget
            while top_level_widget.parent():
                top_level_widget = top_level_widget.parent()

            self.particle_system = StartupParticleSystem(top_level_widget)
            self.particle_system.resize(top_level_widget.size())
            self.logger.info("粒子系统初始化完成")

    def trigger_celebration_particles(self, card_widget: QtWidgets.QWidget):
        """触发庆祝粒子效果 🎉"""
        try:
            self.log_interaction_event("particle_effect", f"触发粒子庆祝效果")

            # 确保粒子系统已初始化
            self.ensure_particle_system(card_widget)

            if self.particle_system:
                # 计算卡片中心点在顶级窗口中的全局坐标
                card_center = card_widget.rect().center()
                global_center = card_widget.mapToGlobal(card_center)

                # 转换为粒子系统父窗口的本地坐标
                parent_widget = self.particle_system.parent()
                if parent_widget:
                    local_center = parent_widget.mapFromGlobal(global_center)

                    # 触发粒子效果
                    self.particle_system.trigger_startup_effect(local_center)
                    self.logger.info(f"粒子效果已触发，位置: {local_center}")
                else:
                    # 如果无法获取父窗口，使用卡片的相对位置
                    self.particle_system.trigger_startup_effect(card_center)
                    self.logger.info(f"粒子效果已触发（相对位置）: {card_center}")
            else:
                self.logger.warning("粒子系统未初始化，无法触发效果")

        except Exception as e:
            error_msg = f"触发粒子效果失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
            # 粒子效果失败不应该影响主要功能，所以不发出错误信号
