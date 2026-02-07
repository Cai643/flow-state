import time
import multiprocessing
import traceback
import json
from queue import Empty

def ai_monitor_worker(msg_queue, running_event, ai_busy_flag=None):
    """
    独立进程：AI 监控 Worker (新版)
    负责：
    1. 获取当前焦点窗口信息 (FocusDetector)
    2. 调用 Ollama 进行语义分析 (AIProcessor)
    3. 解析 JSON 结果并存入数据库 (HistoryManager)
    4. 推送到 UI 队列
    """
    print(f"【AI监控进程】启动 (PID: {multiprocessing.current_process().pid})...")
    
    try:
        # 导入新版检测器组件
        # 注意：在子进程中导入，避免主进程上下文污染
        from app.service.detector.detector_data import FocusDetector
        from app.service.detector.detector_logic import analyze
        from app.data import ActivityHistoryManager
        
        # 初始化组件
        focus_detector = FocusDetector(check_interval=50.0)
        focus_detector.start()
        
        history_manager = ActivityHistoryManager()
        
        # 状态追踪
        last_analysis_time = 0
        last_analyzed_window = None # 记录上次分析过的窗口
        ANALYSIS_INTERVAL = 60  # 加快分析频率 (原为10秒)
        
        current_focus_start = time.time()
        last_window_title = ""
        
        # 新增：全局专注计时器 (跨窗口、跨分析周期)
        # 用于记录连续专注的时长
        global_focus_start_time = None
        
        # 新增：当前状态计时器 (用于娱乐提醒)
        # 记录当前状态 (status) 是从什么时候开始的
        current_status_start_time = time.time()
        last_status_type = "focus" # 默认初始状态
        entertainment_block_start = 0
        MICRO_BREAK_SEC = 90
        
        while running_event.is_set():
            start_loop = time.time()
            
            # --- 检查来自 UI 的重置信号 ---
            try:
                import os
                if os.path.exists("reset_focus.signal"):
                    print("[AI Worker] Received reset signal from UI. Resetting focus timer.")
                    global_focus_start_time = None
                    # 也可以选择重置 current_status_start_time，视需求而定
                    current_status_start_time = time.time() 
                    os.remove("reset_focus.signal")
            except Exception as e:
                print(f"[AI Worker] Error checking signal file: {e}")
            # ---------------------------
            
            try:
                # 1. 获取基础焦点数据 (高频)
                focus_info = focus_detector.get_current_focus()
                
                if not focus_info:
                    time.sleep(1)
                    continue
                    
                window_title = focus_info.get("window_title", "")
                process_name = focus_info.get("process_name", "")
                
                # 简单的状态重置检测
                if window_title != last_window_title:
                    current_focus_start = time.time()
                    last_window_title = window_title
                
                duration = time.time() - current_focus_start
                
                # 2. AI 深度分析
                # 触发条件: 
                # A. 持续时间 > 5秒 (避免抖动)
                # B. (距离上次分析超过间隔 OR 窗口标题发生了变化)
                #    这里我们加入 "窗口变化" 作为触发条件，实现"拿到结果就触发"
                #    同时保留最小间隔限制，防止同一窗口频繁重复分析
                
                ai_result = None
                summary = ""
                status = "focus" # 默认状态
                
                # 检查是否是新窗口（与上次分析时的窗口不同）
                # 注意：last_window_title 是用来判断是否重置计时的，这里我们需要一个变量记录"上次分析过的窗口"
                # 但简单起见，如果 duration > 5 且 还没分析过当前窗口，就应该触发
                
                # 简化逻辑：只要满足时长，且 (时间间隔够了 OR 是个新任务)，就尝试分析
                # 为了防止同一任务刷屏，我们引入一个标志位
                
                should_analyze = False
                if duration > 5:
                    # 场景1: 这是一个新窗口，且还没被分析过 (利用 last_analysis_time 粗略控制是不够的)
                    # 我们需要记录上一次成功分析的窗口名
                    if 'last_analyzed_window' not in locals():
                        last_analyzed_window = None
                        
                    if window_title != last_analyzed_window:
                         should_analyze = True
                    # 场景2: 同一窗口停留很久了，定期重新分析一下 (比如每60秒)，以免漏掉状态变化
                    elif (time.time() - last_analysis_time > ANALYSIS_INTERVAL): 
                         should_analyze = True
                         
                if should_analyze:
                    # --- 错峰执行检查 (已移除，允许并行) ---
                    # if ai_busy_flag and ai_busy_flag.value:
                    #     print(f"[AI Worker] AI正忙(Web端占用)，跳过本次实时分析: {window_title}")
                    #     ... (代码已移除以支持并行)
                        
                    try:
                        ai_data = None
                        json_str = ""
                        
                        # 1. 优先检查空值情况 (如果窗口标题或进程名为空)
                        if not window_title.strip() or not process_name.strip():
                             print(f"[AI Worker] 检测到空窗口或进程名，判定为锁屏离开: '{window_title}' | '{process_name}'")
                             ai_data = {
                                 "状态": "娱乐", 
                                 "活动摘要": "锁屏离开"
                             }
                        
                        # 2. 如果不是空值，则调用 AI 分析
                        if ai_data is None:
                            prompt = f"窗口: '{window_title}' | 进程: {process_name} | 持续: {duration:.2f}s"
                            print(f"[AI Worker] 请求分析: {prompt}")
                            
                            # 调用 Ollama
                            json_str = analyze(prompt)
                            
                            # 解析 JSON
                            ai_data = json.loads(json_str)
                        
                        # 提取关键字段
                        # 兼容 AI 可能返回的不同字段名 (容错)
                        status_raw = ai_data.get("状态", "focus")
                        # 简单的状态映射
                        if "娱乐" in status_raw or "休息" in status_raw:
                            status = "entertainment"
                        elif "Lock Screen" in window_title: # 特殊处理锁屏
                            status = "idle"
                        elif "工作" in status_raw or "学习" in status_raw:
                            status = "work"
                        else:
                            status = "focus"
                            
                        summary = ai_data.get("活动摘要", f"使用 {process_name}")
                        
                        # 打印调试
                        print(f"[AI Worker] 分析结果: {status} | {summary}")
                        
                        last_analysis_time = time.time()
                        last_analyzed_window = window_title # 标记已分析
                        
                        # 3. 存入数据库
                        # 注意：这里我们把 raw_data 存为 JSON 字符串以便后续回溯
                        raw_data_str = json.dumps({
                            "window": window_title,
                            "process": process_name,
                            "ai_raw": ai_data
                        }, ensure_ascii=False)
                        
                        history_manager.update(status, summary=summary, raw_data=raw_data_str)
                        
                        # 构造推送到 UI 的消息
                        # 修改持续专注时间的逻辑：
                        # 使用本地维护的 global_focus_start_time 来计算连续时长
                        
                        current_time = time.time()
                        if status != last_status_type:
                            current_status_start_time = current_time
                            if status == 'entertainment':
                                if entertainment_block_start == 0:
                                    entertainment_block_start = current_time
                            else:
                                if last_status_type == 'entertainment' and entertainment_block_start > 0:
                                    last_entertainment_duration = int(current_time - entertainment_block_start)
                                    entertainment_block_start = 0
                            last_status_type = status
                        if status == 'entertainment':
                            current_activity_duration = int(current_time - entertainment_block_start) if entertainment_block_start else 0
                        else:
                            current_activity_duration = 0
                        if status in ['work', 'focus']:
                            if global_focus_start_time is None:
                                global_focus_start_time = current_time
                            total_focus_duration = int(current_time - global_focus_start_time)
                        elif status == 'entertainment':
                            ent_elapsed = int(current_time - entertainment_block_start) if entertainment_block_start else 0
                            if global_focus_start_time is not None and ent_elapsed > MICRO_BREAK_SEC:
                                global_focus_start_time = None
                            total_focus_duration = int(current_time - global_focus_start_time) if global_focus_start_time else 0
                        else:
                            global_focus_start_time = None
                            total_focus_duration = 0
                        
                        ui_msg = {
                            "status": status,
                            "duration": total_focus_duration, # 专注总时长 (给主界面)
                            "current_activity_duration": current_activity_duration, # 当前活动时长 (给提醒逻辑)
                            "current_window_duration": int(duration), # 窗口停留时长
                            "message": summary,  # UI 上显示摘要
                            "timestamp": time.strftime("%H:%M:%S"),
                            "debug_info": f"AI: {status_raw}"
                        }
                        
                        if not msg_queue.full():
                            msg_queue.put(ui_msg)
                            
                    except json.JSONDecodeError:
                        print(f"[AI Worker] JSON 解析失败: {json_str}")
                    except Exception as e:
                        print(f"[AI Worker] AI 分析出错: {e}")
                
                # 如果没有触发 AI 分析，也可以推送一个轻量级的心跳包给 UI (可选)
                # 或者依靠上面的 AI 分析结果来更新
                pass
                
            except Exception as e:
                print(f"【AI监控进程】循环错误: {e}")
                traceback.print_exc()
            
            # 控制循环频率
            elapsed = time.time() - start_loop
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
                
    except Exception as e:
        print(f"【AI监控进程】致命错误: {e}")
        traceback.print_exc()
    finally:
        if 'focus_detector' in locals():
            focus_detector.stop()
        print("【AI监控进程】已退出")
