from app.data import get_db_connection

class ActivityDAO:
    """活动日志数据访问对象"""
    
    @staticmethod
    def insert_log(status: str, duration: int):
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO activity_logs (status, duration) VALUES (?, ?)',
                (status, duration)
            )
            conn.commit()

class StatsDAO:
    """统计数据访问对象"""
    
    @staticmethod
    def update_daily_stats(date_obj, status: str, duration: int):
        """增量更新每日统计"""
        col_name = f"total_{status}_time"
        # 仅处理有效状态字段
        if status not in ['focus', 'work', 'entertainment']:
            return

        with get_db_connection() as conn:
            # Upsert (Insert or Update)
            conn.execute(f'''
                INSERT INTO daily_stats (date, {col_name}) 
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET 
                {col_name} = {col_name} + ?
            ''', (date_obj, duration, duration))
            conn.commit()

    @staticmethod
    def get_daily_summary(date_obj):
        """获取某日的统计数据"""
        with get_db_connection() as conn:
            row = conn.execute(
                'SELECT * FROM daily_stats WHERE date = ?', (date_obj,)
            ).fetchone()
            if row:
                return dict(row)
        return None

class OcrDAO:
    """OCR 记录数据访问对象"""
    
    @staticmethod
    def insert_record(content: str, app_name: str, screenshot_path: str = None):
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO ocr_records (content, app_name, screenshot_path) VALUES (?, ?, ?)',
                (content, app_name, screenshot_path)
            )
            conn.commit()

    @staticmethod
    def get_recent_records(limit=50):
        """获取最近的 OCR/浏览记录"""
        with get_db_connection() as conn:
            rows = conn.execute(
                'SELECT id, timestamp, app_name, window_title, content FROM ocr_records ORDER BY timestamp DESC LIMIT ?',
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
