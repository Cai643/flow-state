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
        focus_detector = FocusDetector(check_interval=1.0)
        focus_detector.start()
        
        history_manager = ActivityHistoryManager()
        
        # 状态追踪
        last_analysis_time = 0
        last_analyzed_window = None # 记录上次分析过的窗口
        ANALYSIS_INTERVAL = 3  # 加快分析频率 (原为10秒)
        
        current_focus_start = time.time()
        last_window_title = ""
        
        # 新增：全局专注计时器 (跨窗口、跨分析周期)
        # 用于记录连续专注的时长
        global_focus_start_time = None
        
        # 新增：保存上一次的 AI 分析结果，用于在不分析时维持状态
        last_ai_status = "focus"
        last_ai_summary = "准备就绪"
        last_ai_raw = "focus"
        
        while running_event.is_set():
            start_loop = time.time()
            
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
                    # 场景2: 同一窗口停留很久了，定期重新分析一下 (比如每30秒)，以免漏掉状态变化
                    elif (time.time() - last_analysis_time > 30): 
                         should_analyze = True
                         
                if should_analyze:
                    # --- 错峰执行检查 ---
                    if ai_busy_flag and ai_busy_flag.value:
                        print(f"[AI Worker] AI正忙(Web端占用)，跳过本次实时分析: {window_title}")
                        # 虽然跳过 AI 分析，但我们仍需要记录这条活动 (使用默认/上一次状态)
                        status = last_ai_status 
                    else:
                        prompt = f"窗口: '{window_title}' | 进程: {process_name} | 持续: {duration:.2f}s"
                        # print(f"[AI Worker] 请求分析: {prompt}")
                        
                        try:
                            # 调用 Ollama
                            json_str = analyze(prompt)
                            
                            # 解析 JSON
                            ai_data = json.loads(json_str)
                            
                            # 提取关键字段
                            status_raw = ai_data.get("状态", "focus")
                            if "娱乐" in status_raw or "休息" in status_raw:
                                status = "entertainment"
                            elif "工作" in status_raw or "学习" in status_raw:
                                status = "work"
                            else:
                                status = "focus"
                                
                            summary = ai_data.get("活动摘要", f"使用 {process_name}")
                            
                            # 更新缓存
                            last_ai_status = status
                            last_ai_summary = summary
                            last_ai_raw = status_raw
                            
                            # print(f"[AI Worker] 分析结果: {status} | {summary}")
                            
                            last_analysis_time = time.time()
                            last_analyzed_window = window_title # 标记已分析
                            
                            # 3. 存入数据库
                            raw_data_str = json.dumps({
                                "window": window_title,
                                "process": process_name,
                                "ai_raw": ai_data
                            }, ensure_ascii=False)
                            
                            history_manager.update(status, summary=summary, raw_data=raw_data_str)
                            
                        except Exception as e:
                            print(f"[AI Worker] AI 分析出错: {e}")
                            status = last_ai_status
                            summary = last_ai_summary
                            status_raw = last_ai_raw

                else:
                    # 如果不分析，沿用上一次的状态
                    status = last_ai_status
                    summary = last_ai_summary
                    status_raw = last_ai_raw
                
                # --- 构造推送到 UI 的消息 (无论是否分析都要推送) ---
                current_time = time.time()
                
                # 1. 维护当前状态的持续时间 (用于娱乐提醒)
                # 重新初始化变量 (如果之前被 SearchReplace 覆盖了)
                if 'current_status_start_time' not in locals():
                    current_status_start_time = current_time
                if 'last_status_type' not in locals():
                    last_status_type = "focus"
                
                if status != last_status_type:
                    current_status_start_time = current_time
                    last_status_type = status
                    
                current_activity_duration = int(current_time - current_status_start_time)
                
                # 2. 维护专注总时长 (用于主界面显示)
                if status in ['work', 'focus']:
                    if global_focus_start_time is None:
                        global_focus_start_time = current_time
                    
                    total_focus_duration = int(current_time - global_focus_start_time)
                else:
                    global_focus_start_time = None
                    total_focus_duration = 0 
                
                ui_msg = {
                    "status": status,
                    "duration": total_focus_duration, 
                    "current_activity_duration": current_activity_duration,
                    "current_window_duration": int(duration),
                    "message": summary, 
                    "timestamp": time.strftime("%H:%M:%S"),
                    "debug_info": f"AI: {status_raw}"
                }
                
                if not msg_queue.full():
                    msg_queue.put(ui_msg)
                
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
