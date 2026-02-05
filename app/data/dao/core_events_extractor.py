import sys
import os
import re
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.core.database import get_db_connection, get_core_events_db_connection, init_db

def clean_title(title, app_name):
    """
    清洗窗口标题，去除噪音 (增强版)
    """
    if not title:
        return "Unknown Task"
    
    t = title.strip()
    app_lower = app_name.lower()
    
    # 0. Manual 手动会话特殊处理
    if app_lower == "manual":
        # Manual 会话的 window_title 即为用户输入的摘要，直接返回
        return t

    # 1. 浏览器通用清洗 (Edge, Chrome, Firefox)
    if any(browser in app_lower for browser in ['edge', 'chrome', 'firefox', 'browser']):
        # 提取核心网站名 (简单关键词匹配)
        keywords = {
            'Gemini': 'Google Gemini',
            'ChatGPT': 'ChatGPT',
            'GitHub': 'GitHub',
            'Stack Overflow': 'Stack Overflow',
            '飞书': '飞书/Feishu',
            'Bilibili': 'Bilibili',
            'YouTube': 'YouTube',
            'Google': 'Google Search',
            'Bing': 'Bing Search',
            'DeepSeek': 'DeepSeek'
        }
        for k, v in keywords.items():
            if k.lower() in t.lower():
                return v # 直接归类为大类
        
        # 如果没有关键词，只去除后缀
        t = re.sub(r' - Microsoft Edge.*', '', t)
        t = re.sub(r' - Google Chrome.*', '', t)
        t = re.sub(r' 和另外 \d+ 个页面.*', '', t) # Edge 多标签后缀
        t = re.sub(r' and \d+ more pages.*', '', t)

    # 2. 编辑器/IDE 清洗 (VSCode, Trae, JetBrains, Python)
    elif any(ide in app_lower for ide in ['code', 'trae', 'pycharm', 'idea', 'studio', 'python']):
        # 典型的 VSCode/Trae 格式: "filename.py - project - VSCode"
        
        # 策略：取第一个分隔符前的部分作为文件名
        # 假设文件名不包含 " - "
        if " - " in t:
            parts = t.split(" - ")
            # 通常第一部分是文件名
            t = parts[0]
            
        # 如果包含路径分隔符，只取文件名
        if "\\" in t or "/" in t:
            t = os.path.basename(t)
            
    # 3. 视频/娱乐应用清洗 (Bilibili)
    elif "哔哩哔哩" in app_lower or "bilibili" in app_lower:
        # 提取番剧名/UP主名 (通常在第一个破折号前)
        # 格式: "番剧名 - 集数名" 或 "视频标题 - UP主"
        if "-" in t:
            t = t.split("-")[0].strip()
        elif "_" in t: # 有些可能是下划线
            t = t.split("_")[0].strip()
            
    # 4. 通用去噪
    # 去除通知数 (1)
    t = re.sub(r'^\(\d+\)\s*', '', t)
    
    # 4. 去除多余空格
    t = t.strip()
    
    return t if t else app_name

def extract_core_events(target_date):
    """
    提取指定日期的核心事件 (包含 Focus 和 Entertainment)
    1. 过滤 (>120s)
    2. 聚合 (App + Title)
    3. 排序 (Top 3 Focus, Top 2 Entertainment)
    4. 存储 (core_events)
    """
    print(f"Processing core events for {target_date}...")
    
    start_ts = f"{target_date} 00:00:00"
    end_ts = f"{target_date} 23:59:59"
    
    with get_db_connection() as conn_main, get_core_events_db_connection() as conn_core:
        cursor_main = conn_main.cursor()
        cursor_core = conn_core.cursor()
        
        # 先清除当天的旧数据 (支持重跑)
        cursor_core.execute("DELETE FROM core_events WHERE date = ?", (target_date,))

        # 定义要提取的类别和对应的 status
        categories = {
            'focus': ['work', 'focus'],
            'entertainment': ['entertainment']
        }

        for cat, statuses in categories.items():
            status_placeholder = ','.join(['?'] * len(statuses))
            # --- Step 1: 硬过滤 ---
            # 查 status IN (...) 且 duration > 30 (放宽到 30s)
            query = f'''
                SELECT process_name, window_title, duration 
                FROM window_sessions
                WHERE start_time BETWEEN ? AND ?
                AND status IN ({status_placeholder})
                AND duration > 30
            '''
            params = [start_ts, end_ts] + statuses
            cursor_main.execute(query, params)
            
            rows = cursor_main.fetchall()
            
            if not rows and cat == 'focus':
                # [兜底逻辑] 如果 Focus 没找到，尝试找 Unknown 或其他状态中最长的
                print(f"  [Fallback] No explicit focus found, searching for ANY significant activity...")
                fallback_query = '''
                    SELECT process_name, window_title, duration 
                    FROM window_sessions
                    WHERE start_time BETWEEN ? AND ?
                    AND duration > 60
                    ORDER BY duration DESC
                    LIMIT 5
                '''
                cursor_main.execute(fallback_query, [start_ts, end_ts])
                rows = cursor_main.fetchall()
                # 标记为 'misc' 以便区分，但存入数据库时仍可暂用 focus 或新建 misc 类别
                # 这里为了兼容性，仍存为 focus，但在标题上做标记
                # 仅当完全没有行时才跳过
                if not rows:
                    print(f"  No significant activity found at all for {target_date}")
                    continue
            elif not rows:
                 print(f"  No {cat} sessions found for {target_date}")
                 continue

            # --- Step 2: 全局聚合 (New Logic) ---
            # 不再依赖相邻合并，而是将全天所有的 (App, Cleaned Title) 进行累加
            events_map = {}
            
            for row in rows:
                app = row['process_name'] or "Unknown"
                raw_title = row['window_title'] or ""
                dur = row['duration']
                
                # 清洗标题
                ct = clean_title(raw_title, app)
                
                # 组合键 (App, Cleaned Title)
                key = (app, ct)
                
                if key not in events_map:
                    events_map[key] = {'duration': 0, 'count': 0}
                
                # 累加时长和次数
                events_map[key]['duration'] += dur
                events_map[key]['count'] += 1
                
            # --- Step 3: 排序 Top-N ---
            event_list = []
            for (app, title), stats in events_map.items():
                event_list.append({
                    'app': app,
                    'title': title,
                    'duration': stats['duration'],
                    'count': stats['count']
                })
                
            # 按总时长降序排列
            event_list.sort(key=lambda x: x['duration'], reverse=True)
            
            # Take Top N for each category (Top 3 Focus, Top 2 Entertainment)
            limit = 3 if cat == 'focus' else 2
            top_events = event_list[:limit]
            
            # --- Step 4: 存储 ---
            for rank, event in enumerate(top_events, 1):
                cursor_core.execute('''
                    INSERT INTO core_events (date, app_name, clean_title, total_duration, event_count, rank, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    target_date,
                    event['app'],
                    event['title'],
                    event['duration'],
                    event['count'],
                    rank,
                    cat
                ))
                print(f"  [{cat.upper()}] Rank {rank}: [{event['app']}] {event['title']} ({int(event['duration']/60)}m)")
            
        conn_core.commit()
        print("Done.")

def run_backfill(days=3):
    """回溯最近 N 天的数据"""
    init_db() # Ensure table exists
    
    today = datetime.now().date()
    for i in range(days):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        extract_core_events(d_str)

if __name__ == "__main__":
    # 跑最近 4 天 (覆盖 21, 22, 23, 24)
    run_backfill(4)
    
    # 手动指定跑 2026-01-21
    extract_core_events('2026-01-21')
