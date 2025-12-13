import time
import threading
import sys
import os
from typing import Callable, Dict, Optional, Tuple

print("[INIT] Starting imports...", file=sys.stderr)
sys.stderr.flush()

# Optional: cv2 (known to hang on some Windows 3.14 builds)
CV2_AVAILABLE = False
try:
    import cv2  # type: ignore
    print("[INIT] cv2 imported", file=sys.stderr)
    sys.stderr.flush()
    CV2_AVAILABLE = True
except Exception as e:
    print(f"[INIT] cv2 not available (expected on Windows 3.14): {e}", file=sys.stderr)
    sys.stderr.flush()
    cv2 = None

try:
    import numpy as np  # type: ignore
    print("[INIT] numpy imported", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"[INIT] numpy import failed: {e}", file=sys.stderr)
    sys.stderr.flush()
    np = None

try:
    from PIL import ImageGrab  # type: ignore
    print("[INIT] PIL imported", file=sys.stderr)
    sys.stderr.flush()
except Exception as e:
    print(f"[INIT] PIL import failed: {e}", file=sys.stderr)
    sys.stderr.flush()
    ImageGrab = None

# Try pynput with timeout
PYNPUT_AVAILABLE = False
try:
    from pynput import keyboard, mouse  # type: ignore
    print("[INIT] pynput imported", file=sys.stderr)
    sys.stderr.flush()
    PYNPUT_AVAILABLE = True
except Exception as e:
    print(f"[INIT] pynput not available: {e}, using mock", file=sys.stderr)
    sys.stderr.flush()
    PYNPUT_AVAILABLE = False
    # Mock classes
    class keyboard:
        class Listener:
            def __init__(self, on_press=None):
                self.on_press = on_press
            def start(self):
                print("[keyboard.Listener] (mocked, no-op)", file=sys.stderr)
            def stop(self):
                pass
    class mouse:
        class Listener:
            def __init__(self, on_move=None, on_click=None):
                self.on_move = on_move
                self.on_click = on_click
            def start(self):
                print("[mouse.Listener] (mocked, no-op)", file=sys.stderr)
            def stop(self):
                pass

# 导入 API 模块
print("[INIT] Importing API module...", file=sys.stderr)
try:
    from ai.model import API
    print("[INIT] API imported successfully", file=sys.stderr)
except ImportError:
    # 尝试相对导入（如果在 IDE 中直接运行 tool.py）
    try:
        import sys
        sys.path.append('..')
        from model import API
        print("[INIT] API imported (relative) successfully", file=sys.stderr)
    except Exception as e:
        print(f"[INIT] Warning: Could not import API module: {e}", file=sys.stderr)
        API = None

print("[INIT] All imports completed", file=sys.stderr)

def _get_analysis_safe(payload: dict) -> dict:
    if API and hasattr(API, 'get_analysis'):
        return API.get_analysis(payload)
    return {'status': 'unknown', 'duration': 0, 'message': 'API.get_analysis not available'}

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
        try:
            self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
            self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
            
            self.keyboard_listener.start()
            self.mouse_listener.start()
            print("[InputMonitor] 输入监控已启动...")
        except Exception as e:
            print(f"[InputMonitor] Warning: 启动失败: {e}")
            self.running = False

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
        :return: OpenCV 格式的图像帧 (BGR) 或 None
        """
        if not CV2_AVAILABLE or not ImageGrab:
            return None
        try:
            screen = ImageGrab.grab()
            # 将 PIL 图像转换为 numpy 数组
            img_np = np.array(screen)
            # PIL 使用 RGB，OpenCV 使用 BGR，需要转换颜色空间
            frame = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"[ScreenAnalyzer] Screen capture failed: {e}", file=sys.stderr)
            return None

    def analyze_frame(self, frame):
        """
        对图像帧进行分析（需根据具体需求微调）
        
        当前实现：
        1. 计算平均亮度。
        2. 使用 Canny 算法检测边缘，评估画面复杂度。
        
        :param frame: OpenCV 图像帧 或 None
        :return: 包含分析结果的字典
        """
        if frame is None or not CV2_AVAILABLE:
            return {
                "resolution": (0, 0),
                "average_brightness": 128,
                "edge_density": 0.01,
                "is_complex_scene": False
            }

        try:
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
        except Exception as e:
            print(f"[ScreenAnalyzer] Frame analysis failed: {e}", file=sys.stderr)
            return None

    def detect_content_type(self, current_frame, prev_frame):
        """
        [新增功能] 区分 娱乐(视频/游戏) 与 学习(文档/代码)
        核心逻辑：基于画面变化率（光流法/帧差法简化版）
        
        :param current_frame: 当前帧
        :param prev_frame: 上一帧
        :return: 判定结果字符串, 变化率数值
        """
        if current_frame is None or prev_frame is None or not CV2_AVAILABLE:
            return "未知", 0.0

        try:
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
        except Exception as e:
            print(f"[ScreenAnalyzer] Content detection failed: {e}", file=sys.stderr)
            return "未知", 0.0


# ========== 便于外部调用的封装函数 ==========

def gather_sample(
    monitor: InputMonitor,
    analyzer: ScreenAnalyzer,
    prev_frame,
) -> Tuple[Dict, object]:
    """采集一次输入与屏幕分析数据，返回 (payload, current_frame).

    payload 结构示例:
    {
        "key_presses": int,
        "mouse_clicks": int,
        "mouse_distance_pixels": int,
        "screen_change_rate": float,
        "content_type": str,
        "is_complex_scene": bool,
        "recent_activity": list[str],
        "average_brightness": float | None,
        "edge_density": float | None,
    }
    """
    frame = analyzer.capture_screen()
    analysis_stats = analyzer.analyze_frame(frame)
    content_type, change_val = analyzer.detect_content_type(frame, prev_frame)
    input_stats = monitor.get_and_reset_stats()

    payload = {
        "key_presses": input_stats.get("key_presses", 0),
        "mouse_clicks": input_stats.get("mouse_clicks", 0),
        "mouse_distance_pixels": input_stats.get("mouse_distance_pixels", 0),
        "screen_change_rate": change_val,
        "content_type": content_type,
        "is_complex_scene": bool(analysis_stats.get("is_complex_scene", False)) if analysis_stats else False,
        "recent_activity": input_stats.get("recent_activity", []),
        "average_brightness": analysis_stats.get("average_brightness") if analysis_stats else None,
        "edge_density": analysis_stats.get("edge_density") if analysis_stats else None,
    }

    return payload, frame


def stream_monitoring(
    interval: float,
    on_sample: Callable[[Dict], None],
    stop_event: Optional[threading.Event] = None,
):
    """持续采样输入与屏幕数据，并将 payload 交给回调 on_sample。

    - interval: 采样间隔秒数
    - on_sample(payload): 回调处理采样结果（可将数据递交到其他模块/服务）
    - stop_event: 外部传入的 threading.Event，用于优雅停止
    """
    monitor = InputMonitor()
    analyzer = ScreenAnalyzer()
    monitor.start()
    prev_frame = None

    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            payload, prev_frame = gather_sample(monitor, analyzer, prev_frame)
            on_sample(payload)
            time.sleep(interval)
    finally:
        monitor.stop()
        if stop_event:
            stop_event.set()


def start_monitoring_thread(
    interval: float,
    on_sample: Callable[[Dict], None],
) -> threading.Event:
    """启动一个后台线程执行 stream_monitoring，返回可用于停止的事件。"""
    stop_event = threading.Event()
    t = threading.Thread(
        target=stream_monitoring,
        args=(interval, on_sample, stop_event),
        daemon=True,
    )
    t.start()
    return stop_event


def example_on_sample_with_api(payload: Dict):
    """示例回调：调用 API.get_analysis 并打印结果。"""
    try:
        result = _get_analysis_safe({
            'key_presses': payload.get('key_presses', 0),
            'mouse_clicks': payload.get('mouse_clicks', 0),
            'screen_change_rate': payload.get('screen_change_rate', 0.0),
            'is_complex_scene': payload.get('is_complex_scene', False),
        })
        print(f"[analysis] status={result['status']} duration={result['duration']}s msg={result['message']}")
    except Exception as e:
        print(f"analysis error: {e}")


if __name__ == "__main__":
    # 简化测试：直接测试采样和 API 调用，不依赖线程
    print("[*] 初始化工具...")
    try:
        monitor = InputMonitor()
        analyzer = ScreenAnalyzer()
        print("[*] 工具初始化完成。")
        print("[*] 启动输入监听...")
        monitor.start()
        print("[*] 输入监听启动完成。")
        print("[*] 采样一次...")
        payload, frame = gather_sample(monitor, analyzer, None)
        print(f"[*] 采样成功: {payload}")
        result = _get_analysis_safe(payload)
        print(f"[*] 分析结果: {result}")
        monitor.stop()
    except KeyboardInterrupt:
        print("\n[*] 被用户中断。")
    except Exception as e:
        print(f"[!] 错误: {e}")
        import traceback
        traceback.print_exc()
