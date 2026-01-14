import sqlite3
import os
from contextlib import contextmanager

# 数据库文件路径
DB_PATH = os.path.join(os.getcwd(), 'data', 'xiaoliu.db')

@contextmanager
def get_db_connection():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """初始化数据库表结构 (统一管理所有表)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 活动日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                confidence REAL DEFAULT 1.0
            )
        ''')
        
        # 3. OCR 识别记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ocr_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content TEXT,
                app_name TEXT,
                window_title TEXT,
                screenshot_path TEXT,
                tags TEXT
            )
        ''')
        
        # 4. 每日统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_focus_time INTEGER DEFAULT 0,
                total_work_time INTEGER DEFAULT 0,
                total_entertainment_time INTEGER DEFAULT 0,
                pull_back_count INTEGER DEFAULT 0,
                summary_text TEXT
            )
        ''')
        
        # 索引优化
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_logs(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ocr_timestamp ON ocr_records(timestamp)')
        
        conn.commit()
        print(f"[Database] Initialized at {DB_PATH}")

def get_db_path():
    return DB_PATH
