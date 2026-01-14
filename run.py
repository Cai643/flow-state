import sys
import os

# Add the current directory to sys.path to make the 'app' package importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import main
from app.services.web_server import run_server
from app.services.ai_worker import ai_monitor_worker
import multiprocessing

if __name__ == "__main__":
    # Windows 下多进程必须在 __main__ 中启动
    # 使用 freeze_support() 以支持 PyInstaller 打包
    multiprocessing.freeze_support()
    
    # 1. 创建进程间通信队列 (用于 AI 进程向 UI 进程发送状态)
    msg_queue = multiprocessing.Queue()
    
    # 2. 创建控制事件 (用于优雅退出)
    running_event = multiprocessing.Event()
    running_event.set()
    
    # 3. 启动 AI 监控进程
    ai_process = multiprocessing.Process(
        target=ai_monitor_worker, 
        args=(msg_queue, running_event),
        name="AI_Monitor_Process"
    )
    ai_process.start()
    
    # 4. 启动 Web 服务进程 (完全独立，不需要 Queue)
    web_process = multiprocessing.Process(
        target=run_server, 
        kwargs={'port': 8080},
        name="Web_Server_Process"
    )
    web_process.start()
    
    # 5. 启动主程序 GUI (主进程)
    # 将队列传递给 main，以便 UI 能够读取 AI 进程的数据
    try:
        main(msg_queue)
    except KeyboardInterrupt:
        pass
    finally:
        print("【主进程】正在退出，清理子进程...")
        running_event.clear() # 通知 AI 进程退出
        
        # 强制终止 Web 进程 (因为 Flask 没有简单的停止方法)
        if web_process.is_alive():
            web_process.terminate()
            
        # 等待 AI 进程优雅退出
        ai_process.join(timeout=2)
        if ai_process.is_alive():
            ai_process.terminate()
            
        print("【主进程】所有子进程已关闭")
