import sqlite3
import os
from contextlib import contextmanager

# 数据库文件路径
# 使用绝对路径，确保在不同工作目录下（如 Flask 线程中）也能正确找到数据库
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_DIR = os.path.join(BASE_DIR, 'app', 'data', 'dao', 'storage')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
DB_PATH = os.path.join(DB_DIR, 'focus_app.db')
PERIOD_STATS_DB_PATH = os.path.join(DB_DIR, 'period_stats.db')
CORE_EVENTS_DB_PATH = os.path.join(DB_DIR, 'core_events.db')

@contextmanager
def get_db_connection(db_path=None):
    """获取数据库连接的上下文管理器
    Args:
        db_path: 数据库路径，默认为 DB_PATH (focus_app.db)
    """
    target_path = db_path if db_path else DB_PATH
    conn = sqlite3.connect(target_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_period_stats_db_connection():
    """获取 Period Stats 数据库连接"""
    with get_db_connection(PERIOD_STATS_DB_PATH) as conn:
        yield conn

@contextmanager
def get_core_events_db_connection():
    """获取 Core Events 数据库连接"""
    with get_db_connection(CORE_EVENTS_DB_PATH) as conn:
        yield conn

def init_db():
    """初始化数据库表结构 (统一管理所有表)"""
    # 1. 初始化主数据库 (focus_app.db)
    with get_db_connection(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 2. 活动日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                confidence REAL DEFAULT 1.0,
                summary TEXT,
                raw_data TEXT
            )
        ''')
        # 3. 窗口会话表 - 用于记录聚合后的窗口使用时长
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS window_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                window_title TEXT,
                process_name TEXT,
                status TEXT,
                duration INTEGER DEFAULT 0,
                summary TEXT
            )
        ''')
        
        # 尝试添加新字段 (如果表已存在)
        try:
            cursor.execute('ALTER TABLE activity_logs ADD COLUMN summary TEXT')
        except sqlite3.OperationalError:
            pass # 字段已存在
            
        try:
            cursor.execute('ALTER TABLE activity_logs ADD COLUMN raw_data TEXT')
        except sqlite3.OperationalError:
            pass # 字段已存在
        
        # 4. 每日统计表
        # 记录每一天的专注总时长、最高专注持续时间、娱乐总时长、目前持续专注时长，效能指数
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_focus_time INTEGER DEFAULT 0,  -- 专注总时长
                max_focus_streak INTEGER DEFAULT 0,  -- 最高专注持续时间
                total_entertainment_time INTEGER DEFAULT 0, -- 娱乐总时长
                current_focus_streak INTEGER DEFAULT 0, -- 目前持续专注时长
                efficiency_score INTEGER DEFAULT 0,   -- 效能指数
                willpower_wins INTEGER DEFAULT 0,    -- 意志力胜利次数
                summary_text TEXT
            )
        ''')
        
        # 尝试添加新字段 (如果表已存在)
        try:
            cursor.execute('ALTER TABLE daily_stats ADD COLUMN max_focus_streak INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute('ALTER TABLE daily_stats ADD COLUMN current_focus_streak INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute('ALTER TABLE daily_stats ADD COLUMN efficiency_score INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE daily_stats ADD COLUMN willpower_wins INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
            
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_logs(timestamp)')
        conn.commit()

    # 2. 初始化 Core Events 数据库
    with get_db_connection(CORE_EVENTS_DB_PATH) as conn:
        cursor = conn.cursor()
        # 5. 核心事件表 (Core Events)
        # 存储经过漏斗筛选法提取出的每日核心高频事件，供AI写日报使用
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS core_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                app_name TEXT,
                clean_title TEXT,
                total_duration INTEGER,
                event_count INTEGER,
                rank INTEGER, -- 当日排名(1-5)
                category TEXT DEFAULT 'focus' -- 'focus' or 'entertainment'
            )
        ''')
        
        # 尝试添加新字段 (如果表已存在)
        try:
            cursor.execute('ALTER TABLE core_events ADD COLUMN category TEXT DEFAULT "focus"')
        except sqlite3.OperationalError:
            pass
            
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_core_events_date ON core_events(date)')
        conn.commit()

    # 3. 初始化 Period Stats 数据库
    with get_db_connection(PERIOD_STATS_DB_PATH) as conn:
        cursor = conn.cursor()
        # 6. 周期统计表 (Period Stats)
        # 存储按日/按周计算的“致追梦者”核心指标，避免每次生成报告时重复计算
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS period_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,          -- 统计日期
                total_focus INTEGER, -- 专注总时长 (秒)
                total_entertainment INTEGER, -- 娱乐总时长 (秒)
                max_streak INTEGER,  -- 最长心流 (秒)
                willpower_wins INTEGER, -- 意志力胜利次数
                peak_hour INTEGER,   -- 黄金时段 (0-23)
                efficiency_score INTEGER, -- 效能指数 (0-100)
                daily_summary TEXT,  -- 每日核心事项摘要 (AI Summary)
                focus_fragmentation_ratio REAL DEFAULT 0, -- 专注/碎片比 (Avg Focus Dur / Avg Ent Dur)
                context_switch_freq REAL DEFAULT 0, -- 切换频率 (Switches / Hour)
                ai_insight TEXT -- 自动生成的业务价值洞察
            )
        ''')
        
        # 尝试添加新字段 (如果表已存在)
        try:
            cursor.execute('ALTER TABLE period_stats ADD COLUMN daily_summary TEXT')
        except sqlite3.OperationalError: pass
            
        try:
            cursor.execute('ALTER TABLE period_stats ADD COLUMN focus_fragmentation_ratio REAL DEFAULT 0')
        except sqlite3.OperationalError: pass
            
        try:
            cursor.execute('ALTER TABLE period_stats ADD COLUMN context_switch_freq REAL DEFAULT 0')
        except sqlite3.OperationalError: pass
            
        try:
            cursor.execute('ALTER TABLE period_stats ADD COLUMN ai_insight TEXT')
        except sqlite3.OperationalError: pass # 字段已存在
        
        try:
            cursor.execute('ALTER TABLE period_stats ADD COLUMN total_entertainment INTEGER')
        except sqlite3.OperationalError: pass

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_period_stats_date ON period_stats(date)')
        conn.commit()
        
    print(f"[Database] Initialized databases at {DB_DIR}")

def get_db_path():
    return DB_PATH
