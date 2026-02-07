# -*- coding: utf-8 -*-
import sys
import os
import signal
import multiprocessing
import time
import socket
import subprocess
import logging
from logging.handlers import RotatingFileHandler

# Add the current directory to sys.path to make the 'app' package importable
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import DATA_DIR

# --- Logging Setup ---
def setup_logging():
    log_file = os.path.join(DATA_DIR, 'app.log')
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File Handler (Rotating)
    # Max size 5MB, keep 3 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(processName)s: %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console Handler (if not frozen or if needed)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    print(f"Logging initialized. Log file: {log_file}")

# Initialize logging immediately
setup_logging()

def force_exit(signum, frame):
    # 只让主进程打印消息
    if multiprocessing.current_process().name == 'MainProcess':
        print("\n正在退出程序...")
    # 所有进程都立即退出
    os._exit(1)

signal.signal(signal.SIGINT, force_exit)
signal.signal(signal.SIGTERM, force_exit)

# Add the current directory to sys.path to make the 'app' package importable
# sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.ui.main import main
from app.service.API.web_API import run_server
from app.service.monitor_service import ai_monitor_worker
from app.ui.widgets.dialogs.model_selection import show_model_selection

def ensure_ollama_running():
    """检查并启动 Ollama 服务"""
    host = 'localhost'
    port = 11434
    
    # 检查端口是否被占用
    def is_port_open():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    if is_port_open():
        print("Ollama 服务检测：已在运行。")
        return None

    print("Ollama 服务检测：未运行，正在尝试启动...")
    try:
        # 启动 ollama serve
        # 使用 CREATE_NO_WINDOW 隐藏控制台窗口 (仅限 Windows)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
        
        # 等待服务就绪
        print("等待 Ollama 服务启动...")
        for _ in range(10):  # 最多等待 10 秒
            if is_port_open():
                print("Ollama 服务启动成功！")
                return process
            time.sleep(1)
        
        print("警告：Ollama 服务启动超时，可能需要手动启动。")
        return process
    except FileNotFoundError:
        print("错误：未找到 'ollama' 命令。请确保已安装 Ollama 并添加到系统 PATH 中。")
    except Exception as e:
        print(f"启动 Ollama 服务失败: {e}")
    
    return None

if __name__ == "__main__":
    # Windows 下多进程必须在 __main__ 保护下
    # 使用 freeze_support() 来支持 PyInstaller 打包
    multiprocessing.freeze_support()
    
    # 0. 自动启动 Ollama 服务
    ollama_process = ensure_ollama_running()
    
    # 新增: 模型选择
    # 必须在 Ollama 启动后调用，以便获取模型列表
    print("正在启动模型选择窗口...")
    selected_model = show_model_selection()
    
    if not selected_model:
        print("用户取消了模型选择，程序退出。")
        sys.exit(0)
        
    # 设置环境变量，供子进程 (AI Worker) 使用
    os.environ['OLLAMA_MODEL'] = selected_model
    print(f"已选择 AI 模型: {selected_model}")
    
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
    ai_process.daemon = True  # 关键：设置为守护进程
    ai_process.start()
    
    # 4. 启动 Web 服务进程 (完全独立，不需要 Queue)
    web_process = multiprocessing.Process(
        target=run_server, 
        kwargs={'port': 8080, 'ai_busy_flag': ai_busy_flag},
        name="Web_Server_Process"
    )
    web_process.daemon = True  # 关键：设置为守护进程
    web_process.start()
    
    # 5. 启动主程序 GUI (主进程)
    # 将队列传给 main，以便 UI 能够读取 AI 进程的数据
    try:
        main(msg_queue)
    except KeyboardInterrupt:
        pass
    finally:
        print("主进程：正在退出，通知子进程...")
        running_event.clear()  # 通知 AI 进程退出
        
        # 给子进程一点时间优雅退出
        time.sleep(0.5)
        
        print("主进程：退出完成")
