import time
import multiprocessing
import traceback

# 导入必要的业务逻辑
# 注意：在多进程模式下，需要避免导入 PyQt 等 GUI 库
# 因此我们这里只导入纯逻辑类

def ai_monitor_worker(msg_queue, running_event):
    """
    独立进程：AI 监控 Worker
    负责：摄像头采集 -> AI 分析 -> 数据库写入 -> 结果推送到队列
    """
    print(f"【AI监控进程】启动 (PID: {multiprocessing.current_process().pid})...")
    
    try:
        # 在子进程中初始化资源
        # 1. 初始化数据库连接（每个进程需要独立的连接）
        # from app.core.database import init_db
        # init_db() # 确保表存在
        
        # 2. 初始化 AI 分析器
        from app.services.ai.vision import CameraAnalyzer
        from app.services.ai import inference as API
        from app.data import ActivityHistoryManager
        
        analyzer = CameraAnalyzer()
        history_manager = ActivityHistoryManager()
        
        if not analyzer.start():
            print("【AI监控进程】摄像头启动失败！")
            return

        last_frame = None
        
        while running_event.is_set():
            start_time = time.time()
            
            try:
                # 1. 采集数据
                frame = analyzer.capture_frame()
                analysis_stats = analyzer.analyze_frame(frame)
                content_type, change_val = analyzer.detect_content_type(frame, last_frame)
                last_frame = frame
                
                # 2. 准备数据
                monitor_data = {
                    'key_presses': 0,
                    'mouse_clicks': 0,
                    'screen_change_rate': change_val,
                    'is_complex_scene': analysis_stats.get('is_complex_scene', False) if analysis_stats else False
                }
                
                # 3. AI 推理与存储
                if API:
                    result = API.get_analysis(monitor_data)
                    status = result.get('status')
                    
                    if status:
                        # 写入数据库 (ActivityHistoryManager 内部处理)
                        history_manager.update(status)
                    
                    # 4. 推送结果给主进程 UI
                    # 为了防止队列堆积，可以使用 put_nowait 或先判断 full
                    if not msg_queue.full():
                        msg_queue.put(result)
                        
            except Exception as e:
                print(f"【AI监控进程】发生错误: {e}")
                traceback.print_exc()
            
            # 控制循环频率 (约1秒一次)
            elapsed = time.time() - start_time
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
                
    except Exception as e:
        print(f"【AI监控进程】致命错误: {e}")
        traceback.print_exc()
    finally:
        # 清理资源
        if 'analyzer' in locals():
            analyzer.stop()
        print("【AI监控进程】已退出")
