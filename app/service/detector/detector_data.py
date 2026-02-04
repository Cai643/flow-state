import time
import traceback
try:
    from app.service.detector import detector_logic as AI
except ImportError:
    try:
        import detector_logic as AI
    except ImportError:
        pass # Fallback or handle later if AI is strictly required

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import count
from typing import Iterator, Tuple, Optional, Dict, List
import threading
from threading import Event

# 鼠标键盘检测相关
import pynput
from pynput import mouse, keyboard

# 焦点识别相关
import win32gui
import win32process
import psutil

#焦点截图相关
import os
from datetime import datetime
from PIL import ImageGrab
import ctypes
from ctypes import wintypes

# ============ 通用工具函数 ============

def get_cursor_pos() -> Optional[Tuple[int, int]]:
    """获取当前鼠标位置"""
    try:
        # 使用 pynput 获取鼠标位置
        from pynput.mouse import Controller
        mouse_controller = Controller()
        return mouse_controller.position
    except Exception:
        return None

class EventType:
    """事件类型定义"""
    MOUSE_MOVE = "MOUSE_MOVE"
    MOUSE_CLICK = "MOUSE_CLICK"
    MOUSE_SCROLL = "MOUSE_SCROLL"
    KEY_PRESS = "KEY_PRESS"
    KEY_RELEASE = "KEY_RELEASE"
    FOCUS_CHANGE = "FOCUS_CHANGE"

@dataclass
class MouseEvent:
    event_type: str
    x: int
    y: int
    button: Optional[str] = None
    dx: Optional[int] = None
    dy: Optional[int] = None
    pressed: Optional[bool] = None
    distance: Optional[float] = None   # ⭐ 新增：与上一次移动的距离
    timestamp: float = field(default_factory=time.time)

@dataclass
class KeyboardEvent:
    """键盘事件"""
    event_type: str
    key: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class FocusEvent:
    window_title: str
    process_name: str
    process_id: int
    duration: float
    timestamp: float = field(default_factory=time.time)

# ============ 鼠标检测函数 ============

class MouseDetector:
    """鼠标事件检测器"""
    
    def __init__(self):
        self._mouse_listener = None
        self._mouse_events = []
        self._lock = threading.Lock()
        self._running = False
        self._last_pos = None
        
    def _on_move(self, x, y):
        with self._lock:
            distance = None

            if self._last_pos is not None:
                last_x, last_y = self._last_pos
                dx = x - last_x
                dy = y - last_y
                distance = (dx ** 2 + dy ** 2) ** 0.5

            self._last_pos = (x, y)

            self._mouse_events.append(MouseEvent(
                event_type=EventType.MOUSE_MOVE,
                x=x,
                y=y,
                distance=distance
            ))

    
    def _on_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        with self._lock:
            self._mouse_events.append(MouseEvent(
                event_type=EventType.MOUSE_CLICK,
                x=x,
                y=y,
                button=str(button).split('.')[-1],  # 例如: "left", "right"
                pressed=pressed
            ))
    
    def _on_scroll(self, x, y, dx, dy):
        """鼠标滚轮事件"""
        with self._lock:
            self._mouse_events.append(MouseEvent(
                event_type=EventType.MOUSE_SCROLL,
                x=x,
                y=y,
                dx=dx,
                dy=dy
            ))
    
    def start(self):
        """启动鼠标检测"""
        try:
            self._running = True
            self._mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self._mouse_listener.start()
            return True
        except Exception as e:
            print(f"启动鼠标检测失败: {e}")
            return False
    
    def get_events(self) -> List[MouseEvent]:
        """获取所有鼠标事件"""
        with self._lock:
            events = self._mouse_events.copy()
            self._mouse_events.clear()
        return events
    
    def stop(self):
        """停止鼠标检测"""
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

# ============ 键盘检测函数 ============

class KeyboardDetector:
    """键盘事件检测器"""
    
    def __init__(self):
        self._keyboard_listener = None
        self._keyboard_events = []
        self._lock = threading.Lock()
        self._running = False
    
    def _on_press(self, key):
        """按键按下事件"""
        with self._lock:
            try:
                key_str = str(key).replace("'", "")
                if hasattr(key, 'char') and key.char:
                    key_str = key.char
                elif hasattr(key, 'name'):
                    key_str = key.name
                
                self._keyboard_events.append(KeyboardEvent(
                    event_type=EventType.KEY_PRESS,
                    key=key_str
                ))
            except Exception as e:
                print(f"处理按键事件出错: {e}")
    
    def _on_release(self, key):
        """按键释放事件"""
        with self._lock:
            try:
                key_str = str(key).replace("'", "")
                if hasattr(key, 'char') and key.char:
                    key_str = key.char
                elif hasattr(key, 'name'):
                    key_str = key.name
                
                self._keyboard_events.append(KeyboardEvent(
                    event_type=EventType.KEY_RELEASE,
                    key=key_str
                ))
            except Exception as e:
                print(f"处理按键释放事件出错: {e}")
    
    def start(self):
        """启动键盘检测"""
        try:
            self._running = True
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._keyboard_listener.start()
            return True
        except Exception as e:
            print(f"启动键盘检测失败: {e}")
            return False
    
    def get_events(self) -> List[KeyboardEvent]:
        """获取所有键盘事件"""
        with self._lock:
            events = self._keyboard_events.copy()
            self._keyboard_events.clear()
        return events
    
    def stop(self):
        """停止键盘检测"""
        self._running = False
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None

# ============ 焦点识别函数 ============

class FocusDetector:
    """焦点窗口检测器"""
    
    def __init__(self, check_interval: float = 0.5):
        """
        初始化焦点检测器
        
        Args:
            check_interval: 检测间隔(秒)
        """
        self.check_interval = check_interval
        self._last_focus_info = None
        self._running = False
        self._lock = threading.Lock()
        self._focus_events = []
        self._thread = None
        self._stop_event = Event()
        self._focus_start_time = None
        #截图
        self._last_screenshot_time = 0
        self.screenshot_interval = 5  # 秒
        # os.makedirs("screenshot", exist_ok=True)
    
    def _get_active_window_info(self) -> Optional[Dict]:
        """获取当前活动窗口信息"""
        try:
            # 获取前台窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            
            # 获取窗口标题
            window_title = win32gui.GetWindowText(hwnd)
            
            # 获取进程ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            # 获取进程信息
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "Unknown"
            
            return {
                "window_title": window_title,
                "process_name": process_name,
                "process_id": pid,
                "hwnd": hwnd
            }
        except Exception as e:
            print(f"获取活动窗口信息失败: {e}")
            return None
    
    def _detection_thread(self):
        """检测线程"""
        while not self._stop_event.is_set():
            try:
                focus_info = self._get_active_window_info()
                
                # ⭐ 截图逻辑应该放在这里，在获取到 focus_info 之后
                if focus_info:
                    now = time.time()
                    # 每 5 秒截图一次
                    # if now - self._last_screenshot_time >= self.screenshot_interval:
                    #     self._take_screenshot(focus_info)
                    #     self._last_screenshot_time = now
                    
                    with self._lock:
                        # 检查焦点是否改变
                        if self._last_focus_info is None or \
                           self._last_focus_info.get("window_title") != focus_info.get("window_title") or \
                           self._last_focus_info.get("process_name") != focus_info.get("process_name"):
                            
                            # 记录焦点事件
                            now = time.time()

                            # 如果之前有焦点，先计算持续时间
                            if self._focus_start_time is not None:
                                duration = now - self._focus_start_time
                            else:
                                duration = 0.0

                            self._focus_events.append(FocusEvent(
                                window_title=focus_info["window_title"],
                                process_name=focus_info["process_name"],
                                process_id=focus_info["process_id"],
                                duration=duration
                            ))

                            # 更新开始时间
                            self._focus_start_time = now
                            self._last_focus_info = focus_info
                            
            except Exception as e:
                print(f"焦点检测出错: {e}")
            
            # 等待一段时间
            self._stop_event.wait(self.check_interval)
    
    def start(self):
        """启动焦点检测"""
        try:
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._detection_thread, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"启动焦点检测失败: {e}")
            return False
    
    def get_events(self) -> List[FocusEvent]:
        """获取所有焦点事件"""
        with self._lock:
            events = self._focus_events.copy()
            self._focus_events.clear()
        return events
    
    def get_current_focus(self) -> Optional[Dict]:
        """获取当前焦点窗口信息"""
        return self._get_active_window_info()
    
    def stop(self):
        """停止焦点检测"""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
    
    def _take_screenshot(self, focus_info):
        """截图函数 - 修复 DPI 问题"""
        try:
            hwnd = focus_info["hwnd"]
            
            # 关键修复：设置 DPI 感知
            try:
                import ctypes
                # 尝试设置进程为 DPI 感知
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
            
            # 获取窗口矩形（现在应该返回正确的物理坐标）
            rect = win32gui.GetWindowRect(hwnd)
            
            # 可选：使用更精确的 API
            try:
                from ctypes import wintypes
                rect_struct = wintypes.RECT()
                ctypes.windll.dwmapi.DwmGetWindowAttribute(
                    wintypes.HWND(hwnd),
                    wintypes.DWORD(9),  # DWMWA_EXTENDED_FRAME_BOUNDS
                    ctypes.byref(rect_struct),
                    ctypes.sizeof(rect_struct)
                )
                rect = (
                    rect_struct.left,
                    rect_struct.top,
                    rect_struct.right,
                    rect_struct.bottom
                )
            except:
                pass  # 如果失败，使用 GetWindowRect 的结果
            
            # 截图
            img = ImageGrab.grab(rect)
            
            app_name = focus_info["process_name"].replace(".exe", "")
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"screenshot/{app_name}_{ts}.png"
            
            img.save(filename)
            # print(f"截图保存: {filename}")
            
        except Exception as e:
            pass # 暂时忽略截图错误
            # print(f"截图失败: {e}")

# ============ 检测函数 ============

def detect_mouse_events(mouse_detector: MouseDetector):
    """鼠标检测函数 - 有事件则输出，无事件无反应"""
    events = mouse_detector.get_events()
    for event in events:
        if event.event_type == EventType.MOUSE_MOVE:
            if event.distance is not None:
                print(f"[鼠标移动] 位置: ({event.x}, {event.y}) | 移动距离: {event.distance:.2f}px")
            else:
                print(f"[鼠标移动] 位置: ({event.x}, {event.y})")
        elif event.event_type == EventType.MOUSE_CLICK:
            action = "按下" if event.pressed else "释放"
            print(f"[鼠标点击] {event.button}键{action} 位置: ({event.x}, {event.y})")
        elif event.event_type == EventType.MOUSE_SCROLL:
            direction = ""
            if event.dx > 0:
                direction += f"向右滚动{event.dx}"
            elif event.dx < 0:
                direction += f"向左滚动{-event.dx}"
            if event.dy > 0:
                direction += f"向上滚动{event.dy}"
            elif event.dy < 0:
                direction += f"向下滚动{-event.dy}"
            print(f"[鼠标滚轮] {direction} 位置: ({event.x}, {event.y})")

def detect_keyboard_events(keyboard_detector: KeyboardDetector):
    """键盘检测函数 - 有事件则输出，无事件无反应"""
    events = keyboard_detector.get_events()
    for event in events:
        if event.event_type == EventType.KEY_PRESS:
            print(f"[键盘按下] 按键: {event.key}")
        elif event.event_type == EventType.KEY_RELEASE:
            print(f"[键盘释放] 按键: {event.key}")

def detect_focus_events(focus_detector: FocusDetector):
    """焦点识别函数 - 焦点切换则输出，无事件无反应"""
    events = focus_detector.get_events()
    for event in events:
        # 构建信息字符串
        info_str = (
            f"窗口: '{event.window_title}' "
            f"| 进程: {event.process_name} "
            f"| 持续: {event.duration:.2f}s"
        )
        
        try:
            # print(f"[焦点切换] {info_str}") # 可选：先打印原始信息
            ai_result = AI.analyze(info_str)
            # 尝试解析 JSON
            import json
            try:
                if isinstance(ai_result, str):
                    # 尝试清理可能存在的 Markdown 标记
                    clean_result = ai_result.strip()
                    # 移除 ```json 标记
                    if clean_result.startswith("```json"):
                        clean_result = clean_result[7:]
                    elif clean_result.startswith("```"):
                        clean_result = clean_result[3:]
                    
                    # 移除结尾的 ```
                    if clean_result.endswith("```"):
                        clean_result = clean_result[:-3]
                    
                    # 再次去除空白字符
                    clean_result = clean_result.strip()
                    
                    # 打印清洗后的结果，方便调试
                    # print(f"DEBUG: Cleaned Result: {clean_result}")
                    
                    data = json.loads(clean_result)
                    print(f"\n[AI 分析] {json.dumps(data, ensure_ascii=False)}")
                else:
                    print(f"\n[AI 分析] {ai_result}")
            except json.JSONDecodeError:
                print(f"\n[AI 分析] (原始输出) {ai_result}")
                
            print(f"源数据: {info_str}\n")
        except Exception as e:
            print(f"[AI 分析失败] {e}")

# ============ 主函数 ============

def main():
    """主函数：持续检测鼠标、键盘和焦点事件"""
    print("开始系统事件检测...")
    print("=" * 50)
    
    # 初始化检测器
    # mouse_detector = MouseDetector()
    # keyboard_detector = KeyboardDetector()
    focus_detector = FocusDetector(check_interval=0.5)
    
    # 启动检测器
    # print("启动鼠标检测...")
    # mouse_started = mouse_detector.start()
    mouse_started = False
    
    # print("启动键盘检测...")
    # keyboard_started = keyboard_detector.start()
    keyboard_started = False
    
    print("启动焦点检测...")
    focus_started = focus_detector.start()
    
    print("\n检测器状态:")
    print(f"  鼠标检测: {'已启动' if mouse_started else '未启动'}")
    print(f"  键盘检测: {'已启动' if keyboard_started else '未启动'}")
    print(f"  焦点检测: {'已启动' if focus_started else '未启动'}")
    print("\n按 Ctrl+C 停止检测\n")
    
    try:
        # 显示当前焦点信息
        if focus_started:
            current_focus = focus_detector.get_current_focus()
            if current_focus:
                print(f"当前焦点: '{current_focus['window_title']}'")
        
        print("=" * 50)
        
        # 主循环
        while True:
            # 检测鼠标事件
            # if mouse_started:
            #     detect_mouse_events(mouse_detector)
            
            # 检测键盘事件
            # if keyboard_started:
            #     detect_keyboard_events(keyboard_detector)
            
            # 检测焦点事件
            if focus_started:
                detect_focus_events(focus_detector)
            
            # 稍微休眠，避免占用过多CPU
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n检测到中断信号，正在停止...")
    except Exception as e:
        print(f"发生错误: {e}")
        traceback.print_exc()
    finally:
        # 停止所有检测器
        print("正在清理资源...")
        # mouse_detector.stop()
        # keyboard_detector.stop()
        focus_detector.stop()
        print("检测已停止")

if __name__ == "__main__":
    print("系统事件检测程序")
    print("功能:")
    print("  1. 检测鼠标移动、点击、滚轮事件 (已禁用)")
    print("  2. 检测键盘按键按下和释放事件 (已禁用)")
    print("  3. 检测窗口焦点切换事件")
    print()
    
    main()