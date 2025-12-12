import time
import threading
import sys
import os

# 将项目根目录添加到 pythonpath 以便导入兄弟模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2
import numpy as np
from PIL import ImageGrab
# 注意：使用 pynput 需要确保环境已安装该库 (pip install pynput)
from pynput import keyboard, mouse

# 导入 API 模块
try:
    from ai.model import API
except ImportError:
    # 尝试相对导入（如果在 IDE 中直接运行 tool.py）
    try:
        import sys
        sys.path.append('..')
        from model import API
    except Exception as e:
        print(f"Warning: Could not import API module: {e}")
        API = None

class InputMonitor:
    """
    输入监控类：负责捕获键盘和鼠标的操作频率与内容。
    
    功能：
    1. 监听键盘按键，记录按键次数和内容缓存。
    2. 监听鼠标移动、点击，记录点击次数和移动距离。
    """
    def __init__(self):
        # 统计数据
        self.key_count = 0
        self.mouse_count = 0
        self.mouse_distance = 0.0
        self.last_mouse_pos = None
        
        # 状态控制
        self.running = False
        self.keyboard_listener = None
        self.mouse_listener = None
        
        # 存储近期输入内容（仅作示例，实际使用需注意隐私）
        self.input_buffer = []
        self.max_buffer_size = 50

    def on_press(self, key):
        """
        键盘按下回调函数
        :param key: 按下的键对象
        """
        try:
            self.key_count += 1
            # 记录按键内容（转换为字符串）
            try:
                key_str = key.char
            except AttributeError:
                key_str = str(key)
                
            self.input_buffer.append(f"Key: {key_str}")
            # 限制缓冲区大小，防止内存溢出
            if len(self.input_buffer) > self.max_buffer_size:
                self.input_buffer.pop(0)
        except Exception as e:
            print(f"Error in keyboard listener: {e}")

    def on_move(self, x, y):
        """
        鼠标移动回调函数
        :param x: 鼠标当前X坐标
        :param y: 鼠标当前Y坐标
        """
        if self.last_mouse_pos:
            # 计算欧几里得距离累加
            dist = ((x - self.last_mouse_pos[0])**2 + (y - self.last_mouse_pos[1])**2)**0.5
            self.mouse_distance += dist
        self.last_mouse_pos = (x, y)

    def on_click(self, x, y, button, pressed):
        """
        鼠标点击回调函数
        :param x: 点击X坐标
        :param y: 点击Y坐标
        :param button: 点击的按键（左/右/中）
        :param pressed: 是否按下（True为按下，False为松开）
        """
        if pressed:
            self.mouse_count += 1
            self.input_buffer.append(f"Click: {button} at ({x}, {y})")
            if len(self.input_buffer) > self.max_buffer_size:
                self.input_buffer.pop(0)

    def start(self):
        """启动键盘和鼠标监听器（非阻塞模式）"""
        if self.running:
            return
            
        self.running = True
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
        print("[InputMonitor] 输入监控已启动...")

    def stop(self):
        """停止监听器"""
        self.running = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
        print("[InputMonitor] 输入监控已停止。")

    def get_stats(self):
        """获取当前统计数据"""
        return {
            "key_presses": self.key_count,
            "mouse_clicks": self.mouse_count,
            "mouse_distance_pixels": int(self.mouse_distance),
            "recent_activity": self.input_buffer[-5:] # 返回最近5条记录用于预览
        }

    def get_and_reset_stats(self):
        """获取统计数据并重置计数器（用于周期性统计）"""
        stats = self.get_stats()
        self.key_count = 0
        self.mouse_count = 0
        self.mouse_distance = 0.0
        return stats


class ScreenAnalyzer:
    """
    屏幕分析类：使用 OpenCV 进行屏幕内容捕获和基础识别。
    
    功能：
    1. 捕获全屏或指定区域截图。
    2. 将截图转换为 OpenCV 可处理的格式。
    3. 提供基础图像分析（如亮度、边缘检测等），可作为更复杂识别（OCR、物体识别）的基础。
    """
    def __init__(self):
        pass

    def capture_screen(self):
        """
        捕获当前屏幕画面
        :return: OpenCV 格式的图像帧 (BGR)
        """
        # 使用 PIL ImageGrab 获取全屏截图
        try:
            screen = ImageGrab.grab()
            # 将 PIL 图像转换为 numpy 数组
            img_np = np.array(screen)
            # PIL 使用 RGB，OpenCV 使用 BGR，需要转换颜色空间
            frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"Screen capture failed: {e}")
            return None

    def analyze_frame(self, frame):
        """
        对图像帧进行分析（需根据具体需求微调）
        
        当前实现：
        1. 计算平均亮度。
        2. 使用 Canny 算法检测边缘，评估画面复杂度。
        
        :param frame: OpenCV 图像帧
        :return: 包含分析结果的字典
        """
        if frame is None:
            return None

        # 1. 转换为灰度图，减少计算量
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. 边缘检测 (Canny)，阈值可根据实际场景微调
        # 较低的阈值会捕获更多细节，较高的阈值只捕获强边缘
        edges = cv2.Canny(gray, 100, 200)

        # 3. 简单的亮度分析 (0-255)
        avg_brightness = np.mean(gray)
        
        # 4. 画面变化率/复杂度分析（边缘像素占比）
        edge_density = np.count_nonzero(edges) / edges.size
        
        analysis_result = {
            "resolution": frame.shape[:2],
            "average_brightness": avg_brightness,
            "edge_density": edge_density,
            "is_complex_scene": edge_density > 0.05 # 简单判定：边缘多则场景复杂
        }
        
        return analysis_result

    def detect_content_type(self, current_frame, prev_frame):
        """
        [新增功能] 区分 娱乐(视频/游戏) 与 学习(文档/代码)
        核心逻辑：基于画面变化率（光流法/帧差法简化版）
        
        :param current_frame: 当前帧
        :param prev_frame: 上一帧
        :return: 判定结果字符串, 变化率数值
        """
        if current_frame is None or prev_frame is None:
            return "未知", 0.0

        # 1. 转灰度，降低计算量
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        # 2. 计算两帧差异 (绝对差值)
        # 视频/游戏：差异像素多，差异值大
        # 文档/代码：差异像素极少（仅光标移动）
        diff = cv2.absdiff(curr_gray, prev_gray)

        # 3. 二值化差异图，过滤微小噪声（阈值30）
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # 4. 计算非零像素比例 (变化区域占比)
        # countNonZero 返回白色像素数量
        total_pixels = curr_gray.size
        changed_pixels = cv2.countNonZero(thresh)
        change_ratio = changed_pixels / total_pixels

        # 5. 判定阈值 (根据经验设定)
        # 变化率 > 5% 通常意味着正在播放视频或玩游戏
        # 变化率 < 1% 通常意味着正在阅读或打字
        if change_ratio > 0.05:
            return "高动态(娱乐/视频)", change_ratio
        elif change_ratio > 0.01:
            return "中动态(浏览/操作)", change_ratio
        else:
            return "静止(阅读/思考)", change_ratio

    def show_preview(self, frame, edges=None):
        """
        (调试用) 显示当前捕获的画面和边缘检测结果
        按 'q' 键退出预览窗口
        """
        if frame is not None:
            # 缩小尺寸以便查看
            scale = 0.5
            h, w = frame.shape[:2]
            small_frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
            cv2.imshow('Screen Monitor Preview', small_frame)
            
            if edges is not None:
                small_edges = cv2.resize(edges, (int(w*scale), int(h*scale)))
                cv2.imshow('Edge Detection', small_edges)
                
            return cv2.waitKey(1) & 0xFF == ord('q')
        return False


if __name__ == "__main__":
    # --- 模块功能测试代码 ---
    print("=== 初始化监控工具 ===")
    
    # 1. 启动输入监控
    monitor = InputMonitor()
    monitor.start()
    
    # 2. 初始化屏幕分析
    analyzer = ScreenAnalyzer()
    
    try:
        print("正在运行监控测试 (按 Ctrl+C 停止)...")
        start_time = time.time()
        
        # 模拟运行循环
        last_frame = None # 存储上一帧用于对比
        while True:
            # 获取屏幕帧
            frame = analyzer.capture_screen()
            
            # 分析屏幕内容
            analysis_stats = analyzer.analyze_frame(frame)
            
            # [新增] 动态内容检测
            content_type, change_val = analyzer.detect_content_type(frame, last_frame)
            last_frame = frame # 更新上一帧

            # 获取并重置输入统计（每秒一次）
            input_stats = monitor.get_and_reset_stats()
            
            # --- [核心修改] 调用 API 进行分析 ---
            if API:
                # 构造 API 需要的数据格式
                monitor_data = {
                    'key_presses': input_stats['key_presses'],
                    'mouse_clicks': input_stats['mouse_clicks'],
                    'screen_change_rate': change_val,
                    'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
                }
                
                # 获取分析结果
                result = API.get_analysis(monitor_data)
                
                # 打印 AI 分析结果
                print(f"\n[AI 分析] 状态: {result['status'].upper()} | 建议: {result['message']}")
            else:
                print("\n[AI 分析] API 模块未加载，无法分析")

            # 打印实时摘要
            print("--- 实时数据 ---")
            print(f"当前活动判定: [{content_type}] (画面变化率: {change_val*100:.2f}%)")
            print(f"键盘敲击: {input_stats['key_presses']} 次/周期")
            print(f"鼠标点击: {input_stats['mouse_clicks']} 次/周期")
            print(f"鼠标移动: {input_stats['mouse_distance_pixels']} 像素/周期")
            if analysis_stats:
                print(f"屏幕亮度: {analysis_stats['average_brightness']:.2f}")
                print(f"场景复杂度: {'高' if analysis_stats['is_complex_scene'] else '低'} ({analysis_stats['edge_density']:.4f})")
            
            # 预览最近输入（演示内容捕获）
            if input_stats['recent_activity']:
                print(f"最近动作: {input_stats['recent_activity']}")
                
            time.sleep(2) # 每2秒输出一次
            
    except KeyboardInterrupt:
        print("\n测试被用户中断。")
    finally:
        # 清理资源
        monitor.stop()
        cv2.destroyAllWindows()
        print("=== 监控工具已退出 ===")
