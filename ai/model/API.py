import time

class ActivityAnalyzerAPI:
    """
    用户活动分析 API
    根据传入的监控数据（键鼠操作、屏幕动态）判断用户状态，
    并返回相应的提醒建议。
    """
    def __init__(self):
        # 状态阈值配置
        self.ENTERTAINMENT_THRESHOLD_PIXELS = 0.05  # 屏幕变化率 > 5% 视为高动态（视频/游戏）
        self.IDLE_THRESHOLD_SECONDS = 300           # 5分钟无操作视为离开
        
        # 历史状态记录（用于平滑判定，避免误报）
        self.history_window_size = 5
        self.state_history = [] 

        # 状态持续时间追踪
        self.last_status = None
        self.status_start_time = 0

    def analyze(self, monitor_data):
        """
        核心分析接口
        :param monitor_data: 字典，包含 keys: 
               - 'key_presses': int (周期内按键数)
               - 'mouse_clicks': int (周期内点击数)
               - 'screen_change_rate': float (0.0-1.0, 屏幕变化率)
               - 'is_complex_scene': bool (画面是否复杂)
        :return: 字典，包含:
               - 'status': str ('working', 'entertainment', 'idle')
               - 'message': str (给用户的建议/提醒)
               - 'confidence': float (置信度)
        """
        screen_change = monitor_data.get('screen_change_rate', 0.0)
        key_presses = monitor_data.get('key_presses', 0)
        mouse_clicks = monitor_data.get('mouse_clicks', 0)
        
        # --- 简单规则判定逻辑 ---
        
        current_status = "working" # 默认假设在工作
        
        # 1. 判定娱乐：高屏幕动态 + 低输入频率
        # (看视频时通常屏幕一直在动，但很少操作键鼠)
        if screen_change > self.ENTERTAINMENT_THRESHOLD_PIXELS:
            if key_presses < 2 and mouse_clicks < 2:
                current_status = "entertainment"
        
        # 2. 判定空闲：无屏幕变化 + 无输入
        if screen_change < 0.001 and key_presses == 0 and mouse_clicks == 0:
            current_status = "idle"

        # --- 历史平滑处理 ---
        self.state_history.append(current_status)
        if len(self.state_history) > self.history_window_size:
            self.state_history.pop(0)
            
        # 统计最近状态中最频繁的一个（众数）
        final_status = max(set(self.state_history), key=self.state_history.count)
        
        # --- 计算持续时间 ---
        current_time = time.time()
        duration = 0
        
        if final_status != self.last_status:
            self.last_status = final_status
            self.status_start_time = current_time
        else:
            duration = current_time - self.status_start_time
        
        # --- 生成响应 ---
        response = {
            "status": final_status,
            "duration": duration,
            "message": "",
            "raw_data": monitor_data
        }
        
        if final_status == "entertainment":
            response["message"] = "检测到您可能在看视频或玩游戏，记得注意专注时间哦！"
        elif final_status == "working":
            response["message"] = "检测到您正在专注工作，继续保持！"
        elif final_status == "idle":
            response["message"] = "您似乎离开了？"
            
        return response

# 单例模式供外部调用
analyzer = ActivityAnalyzerAPI()

def get_analysis(data):
    """
    外部调用的简单入口函数
    """
    return analyzer.analyze(data)

if __name__ == "__main__":
    # 独立运行模式：启动完整的监控与分析循环
    print("=== 启动 AI 分析服务 (独立模式) ===")
    
    try:
        # 尝试导入工具模块
        import sys
        import os
        # 添加项目根目录到路径
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        from ai.tool.tool import InputMonitor, ScreenAnalyzer
        
        # 初始化监控工具
        monitor = InputMonitor()
        monitor.start()
        analyzer_tool = ScreenAnalyzer()
        
        last_frame = None
        print("正在持续监测用户活动... (按 Ctrl+C 停止)")
        
        while True:
            # 1. 获取数据
            frame = analyzer_tool.capture_screen()
            content_type, change_val = analyzer_tool.detect_content_type(frame, last_frame)
            last_frame = frame
            
            analysis_stats = analyzer_tool.analyze_frame(frame)
            input_stats = monitor.get_and_reset_stats()
            
            # 2. 构造数据包
            monitor_data = {
                'key_presses': input_stats['key_presses'],
                'mouse_clicks': input_stats['mouse_clicks'],
                'screen_change_rate': change_val,
                'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
            }
            
            # 3. API 分析
            result = get_analysis(monitor_data)
            
            # 4. 输出结果
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            status_map = {
                'working': '💻 工作中',
                'entertainment': '🎮 娱乐/视频',
                'idle': '☕ 空闲/离开'
            }
            status_text = status_map.get(result['status'], result['status'])
            
            print(f"[{timestamp}] 状态: {status_text} (置信度: {monitor_data['screen_change_rate']:.3f})")
            if result['message']:
                print(f"   >>> 提醒: {result['message']}")
                
            time.sleep(2)
            
    except ImportError as e:
        print(f"错误: 无法导入监控工具模块 ({e})")
        print("请确保在项目根目录下运行，或已正确配置 PYTHONPATH")
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        if 'monitor' in locals():
            monitor.stop()
