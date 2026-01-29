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
        
        # 新增：当前状态计时器 (用于娱乐提醒)
        # 记录当前状态 (status) 是从什么时候开始的
        current_status_start_time = time.time()
        last_status_type = "focus" # 默认初始状态
        
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
                    # 场景2: 同一窗口停留很久了，定期重新分析一下 (比如每30秒)，以免漏掉状态变化
                    elif (time.time() - last_analysis_time > 30): 
                         should_analyze = True
                         
                if should_analyze:
                    # --- 错峰执行检查 ---
                    if ai_busy_flag and ai_busy_flag.value:
                        print(f"[AI Worker] AI正忙(Web端占用)，跳过本次实时分析: {window_title}")
                        
                        # 虽然跳过 AI 分析，但我们仍需要记录这条活动
                        # 构造一个仅包含基础信息的 raw_data
                        raw_data_str = json.dumps({
                            "window": window_title,
                            "process": process_name,
                            "ai_raw": {} # 空的 AI 数据
                        }, ensure_ascii=False)
                        
                        # 存入数据库 (使用默认状态 focus)
                        history_manager.update("focus", summary=window_title, raw_data=raw_data_str)
                        
                        # 标记为已分析，避免下一轮循环立刻重试
                        last_analysis_time = time.time()
                        last_analyzed_window = window_title
                        
                        # 继续下一次循环
                        continue
                        
                    prompt = f"窗口: '{window_title}' | 进程: {process_name} | 持续: {duration:.2f}s"
                    print(f"[AI Worker] 请求分析: {prompt}")
                    
                    try:
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
                        
                        # --- 维护当前状态的持续时间 (用于娱乐提醒) ---
                        
                        # 初始化变量 (利用 Python 闭包特性，但这里是在循环里，需要放到循环外初始化)
                        # 为了修复这个问题，我们需要把这些变量提升到 while 循环外面
                        # 但为了最小化改动，我们这里用 locals() 检查
                        if 'last_entertainment_end_time' not in locals():
                            last_entertainment_end_time = 0
                        
                        if status == 'entertainment':
                            # 如果从上次娱乐结束到现在 < 30秒 (说明是短暂切换，比如弹窗，或者切歌)
                            # 且上次确实有娱乐记录
                            if 0 < (current_time - last_entertainment_end_time) < 30:
                                # 关键：由于 status 变成了 entertainment，last_status_type 肯定也更新了
                                # 但我们需要恢复之前的 current_status_start_time
                                # 逻辑：如果中断时间很短，我们认为 current_status_start_time 应该保持不变（也就是继承之前的）
                                # 可是 current_status_start_time 在上面 "if status != last_status_type" 时已经被重置为 current_time 了
                                # 所以我们需要一个机制来"回滚"或者"维持"
                                
                                # 修正方案：
                                # 不要在上面直接重置，而是结合宽容度判断
                                pass
                        
                        # --- 重写状态切换逻辑 ---
                        if status != last_status_type:
                            # 只有当：新状态不是娱乐，或者 (新状态是娱乐 且 距离上次娱乐结束超过了30秒) 时，才重置
                            should_reset = True
                            
                            if status == 'entertainment':
                                if 0 < (current_time - last_entertainment_end_time) < 30:
                                    should_reset = False
                                    # 恢复之前的开始时间？
                                    # 此时 current_status_start_time 其实还没变，因为我们还没执行赋值
                                    # 但如果中间夹杂了 focus 状态，current_status_start_time 可能在变成 focus 时变过了
                                    # 所以我们需要一个持久的 entertainment_start_time
                                    pass
                            
                            if should_reset:
                                current_status_start_time = current_time
                            else:
                                # 如果是宽容期内的回归，我们需要把 current_status_start_time 恢复成 (current_time - 之前的累计时长)
                                # 这比较复杂。
                                # 简单做法：引入 cached_entertainment_start_time
                                if 'cached_entertainment_start_time' in locals() and cached_entertainment_start_time > 0:
                                    current_status_start_time = cached_entertainment_start_time

                            last_status_type = status

                        # 计算逻辑
                        current_activity_duration = 0
                        
                        if status == 'entertainment':
                            last_entertainment_end_time = current_time
                            if 'cached_entertainment_start_time' not in locals() or should_reset:
                                cached_entertainment_start_time = current_status_start_time
                            
                            # 持续时间 = 当前 - 缓存的开始时间
                            current_activity_duration = int(current_time - cached_entertainment_start_time)
                        
                        else:
                            # 非娱乐状态
                            # 检查宽容度
                            if 0 < (current_time - last_entertainment_end_time) < 30:
                                # 还在宽容期，显示之前的时长
                                if 'cached_entertainment_start_time' in locals():
                                     current_activity_duration = int(last_entertainment_end_time - cached_entertainment_start_time)
                            else:
                                # 超过宽容度，彻底归零
                                cached_entertainment_start_time = 0
                                current_activity_duration = 0 
                                
                        # -----------------------------------------------
                        
                        # --- 维护专注总时长 (用于主界面显示) ---
                        # 状态判定：如果是工作或专注，维护连续计时
                        if status in ['work', 'focus']:
                            if global_focus_start_time is None:
                                global_focus_start_time = current_time
                                # 如果是刚开始，可以减去当前窗口已经持续的时间，以补偿首次分析的延迟
                                # global_focus_start_time -= duration 
                            
                            total_focus_duration = int(current_time - global_focus_start_time)
                        else:
                            # 如果是娱乐或其他，重置计时器
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
