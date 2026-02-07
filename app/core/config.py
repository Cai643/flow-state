# -*- coding: utf-8 -*-
import os
import sys

def get_app_paths():
    """
    获取应用的关键路径
    Returns:
        tuple: (base_dir, data_dir)
        base_dir: 程序运行根目录 (EXE所在目录 或 源码根目录)
        data_dir: 数据存储目录 (外部 data 文件夹)
    """
    if getattr(sys, 'frozen', False):
        # 打包环境 (PyInstaller)
        # sys.executable 是 EXE 的全路径
        base_dir = os.path.dirname(sys.executable)
        
        # 在 EXE 旁边的 data 文件夹
        data_dir = os.path.join(base_dir, 'data')
    else:
        # 开发环境
        # 假设 config.py 在 app/core/config.py
        # 向上回溯 3 层到项目根目录
        current_file = os.path.abspath(__file__)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # 开发环境数据目录
        data_dir = os.path.join(base_dir, 'app', 'data', 'dao', 'storage')

    return base_dir, data_dir

# 全局初始化路径
BASE_DIR, DATA_DIR = get_app_paths()

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
    except Exception as e:
        print(f"Warning: Could not create data directory {DATA_DIR}: {e}")
