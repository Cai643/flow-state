# -*- coding: utf-8 -*-
import sys
import os

# Add the current directory to sys.path to make the 'app' package importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import main
from app.service.API.web_API import run_server
from app.service.API.thread import ai_monitor_worker
import multiprocessing

if __name__ == "__main__":
    # Windows 下多进程必须在 __main__ 保护下
    # 使用 freeze_support() 来支持 PyInstaller 打包
    multiprocessing.freeze_support()
    
    # 1. 创建进程间通信队列 (用于 AI 进程向 UI 进程发送状态)
    msg_queue = multiprocessing.Queue()
    
    # 新增: AI 占用标志 (True=忙碌, False=空闲)
    # 使用 'b' (boolean) 或 'i' (int) 类型
    ai_busy_flag = multiprocessing.Value('b', False)
    
    # 2. 创建运行标志事件 (控制进程退出)
    running_event = multiprocessing.Event()
    running_event.set()
    
    # 3. 启动 AI 监控进程
    ai_process = multiprocessing.Process(
        target=ai_monitor_worker, 
        args=(msg_queue, running_event, ai_busy_flag),
        name="AI_Monitor_Process"
    )
    ai_process.start()
    
    # 4. 启动 Web 服务进程 (完全独立，不需要 Queue)
    web_process = multiprocessing.Process(
        target=run_server, 
        kwargs={'port': 8080, 'ai_busy_flag': ai_busy_flag},
        name="Web_Server_Process"
    )
    web_process.start()
    
    # 5. 启动主程序 GUI (主进程)
    # 将队列传给 main，以便 UI 能够读取 AI 进程的数据
    try:
        main(msg_queue)
    except KeyboardInterrupt:
        pass
    finally:
        print("主进程：正在退出，清理子进程...")
        running_event.clear() # 通知 AI 进程退出
        
        # 强制停止 Web 服务 (因为 Flask 没有简单的停止方法)
        if web_process.is_alive():
            web_process.terminate()
            
        # 等待 AI 监控进程退出
        ai_process.join(timeout=2)
        if ai_process.is_alive():
            ai_process.terminate()
            
        print("主进程：所有子进程已关闭")
