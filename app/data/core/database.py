import sqlite3
import os
import sys
import shutil
from contextlib import contextmanager
from app.core.config import DATA_DIR, BASE_DIR

# 数据库文件路径 (使用统一配置)
DB_DIR = DATA_DIR

if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR)
    except OSError:
        pass # 可能已存在

DB_PATH = os.path.join(DB_DIR, 'focus_app.db')
PERIOD_STATS_DB_PATH = os.path.join(DB_DIR, 'period_stats.db')
CORE_EVENTS_DB_PATH = os.path.join(DB_DIR, 'core_events.db')

def check_and_restore_db(db_name, target_path):
    """
    检查数据库是否存在，如果不存在且在打包环境中存在模板，则恢复
    """
    if getattr(sys, 'frozen', False):
        if not os.path.exists(target_path):
            # 尝试从临时目录(_MEIPASS)寻找模板
            # 假设打包时将数据库放在了 app/data/dao/storage 下
            # 注意：这取决于 --add-data 的具体配置
            # 尝试常见路径
            possible_template_paths = [
                os.path.join(sys._MEIPASS, 'app', 'data', 'dao', 'storage', db_name),
                os.path.join(sys._MEIPASS, db_name)
            ]
            
            for template_path in possible_template_paths:
                if os.path.exists(template_path):
                    print(f"[Database] Restoring {db_name} from template...")
                    try:
                        shutil.copy2(template_path, target_path)
                        print(f"[Database] Restored {db_name} successfully.")
                        return
                    except Exception as e:
                        print(f"[Database] Failed to restore {db_name}: {e}")

# 在导入模块时执行检查 (或者在 init_db 中执行)
# 为了确保首次使用即有效，最好在 init_db 或连接前执行
# 这里我们选择在模块加载时简单定义，在 get_db_connection 或 init_db 前可能需要确保存在
# 但 init_db 会负责创建表，所以如果只是空库，init_db 足够了。
# 只有当用户希望保留"预设数据"时才需要 restore。
# 鉴于用户提到了"当作初始模板"，我们加上这个逻辑。

check_and_restore_db('focus_app.db', DB_PATH)
check_and_restore_db('period_stats.db', PERIOD_STATS_DB_PATH)
check_and_restore_db('core_events.db', CORE_EVENTS_DB_PATH)

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
