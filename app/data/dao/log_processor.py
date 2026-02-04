import sqlite3
import pandas as pd
import os
import re
import sys
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from app.data.core.database import DB_PATH

# 1. 数据库路径
SOURCE_DB = DB_PATH
TARGET_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage', 'cleaned_data.db')

# 2. 读取数据
def load_data():
    try:
        conn = sqlite3.connect(SOURCE_DB)
        conn.row_factory = sqlite3.Row
        
        # 只读取今天的数据
        # Added window_title to the query
        query = "SELECT start_time, process_name as app, window_title, status as raw_status, duration, summary FROM window_sessions WHERE start_time LIKE '2026-01-21%'"
        
        df = pd.read_sql_query(query, conn)
        # Rename columns to match the logic
        df.rename(columns={'start_time': 'start'}, inplace=True)
        conn.close()
        return df
    except Exception as e:
        print(f"Error reading source DB: {e}")
        return pd.DataFrame()

# 3. 核心算法配置
def get_context(row):
    app = str(row['app']).lower()
    summary = str(row['summary']) if row['summary'] else ""
    
    if any(x in app for x in ['trae', 'python', 'github', 'wps', 'notepad', 'snipping']):
        return 'Dev (开发/文档)'
    if 'msedge' in app:
        if 'flow state' in summary or '飞书' in summary or 'google' in summary.lower():
            return 'Research (研判/查阅)'
        return 'Browsing (浏览)'
    if any(x in app for x in ['weixin', 'wechat', '哔哩哔哩']):
        return 'Social/Media (社交媒体)'
    return 'System (系统)'

# 新增：提取主导主题
def extract_dominant_topic(session_details):
    # session_details 结构: [{'title': '黑色四叶草-xx', 'duration': 900}, ...]
    
    # 1. 统计每个标题的总时长
    title_stats = {}
    for item in session_details:
        # 简单清洗：去掉软件名后缀
        # Ensure title is a string
        title = str(item['title']) if item['title'] else "Unknown"
        clean_title = re.sub(r' - (Microsoft\u200b Edge|Trae|Google Chrome|Visual Studio Code).*', '', title)
        title_stats[clean_title] = title_stats.get(clean_title, 0) + item['duration']
    
    # 2. 找出时长最长的标题
    if not title_stats:
        return "未知活动"
    
    dominant_title = max(title_stats, key=title_stats.get)
    return dominant_title

INTERRUPTION_THRESHOLD = 120

def intelligent_merge(df):
    merged_sessions = []
    current_session = None

    for _, row in df.iterrows():
        context = get_context(row)
        
        # 初始化
        if current_session is None:
            current_session = {
                'start_time': row['start'],
                'end_time': row['start'],
                'context': context,
                'total_duration': row['duration'],
                'apps': {row['app']},
                'details': [row['summary']] if row['summary'] else [],
                'raw_logs': [{'title': row['window_title'], 'duration': row['duration']}] # Store raw logs for topic extraction
            }
            continue

        # 判断逻辑
        is_same_context = (context == current_session['context'])
        is_dev_research = (current_session['context'] == 'Dev (开发/文档)' and context == 'Research (研判/查阅)')
        is_short_interruption = (row['duration'] < INTERRUPTION_THRESHOLD)

        if is_same_context or is_dev_research or is_short_interruption:
            # === 执行合并 ===
            current_session['total_duration'] += row['duration']
            current_session['apps'].add(row['app'])
            if row['summary'] and row['summary'] not in current_session['details']:
                current_session['details'].append(row['summary'])
            
            # Add to raw_logs
            current_session['raw_logs'].append({'title': row['window_title'], 'duration': row['duration']})
            
        else:
            # === 封存当前块，计算 Topic，开启新块 ===
            current_session['topic'] = extract_dominant_topic(current_session['raw_logs'])
            merged_sessions.append(current_session)
            
            current_session = {
                'start_time': row['start'],
                'end_time': row['start'],
                'context': context,
                'total_duration': row['duration'],
                'apps': {row['app']},
                'details': [row['summary']] if row['summary'] else [],
                'raw_logs': [{'title': row['window_title'], 'duration': row['duration']}]
            }

    if current_session:
        current_session['topic'] = extract_dominant_topic(current_session['raw_logs'])
        merged_sessions.append(current_session)
    
    return merged_sessions

# 4. 存储到新数据库
def save_to_new_db(sessions):
    if os.path.exists(TARGET_DB):
        os.remove(TARGET_DB)
        
    conn = sqlite3.connect(TARGET_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aggregated_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            context TEXT,
            topic TEXT,
            total_duration INTEGER,
            apps_involved TEXT,
            details_count INTEGER
        )
    ''')
    
    for s in sessions:
        apps_str = ", ".join([str(a).split('.')[0] for a in s['apps']])
        topic = s.get('topic', 'Unknown')
        
        cursor.execute('''
            INSERT INTO aggregated_sessions (start_time, context, topic, total_duration, apps_involved, details_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (s['start_time'], s['context'], topic, int(s['total_duration']), apps_str, len(s['details'])))
        
    conn.commit()
    conn.close()
    print(f"Successfully saved {len(sessions)} aggregated sessions to {TARGET_DB}")

# 5. 显示结果
def show_results():
    conn = sqlite3.connect(TARGET_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM aggregated_sessions")
    rows = cursor.fetchall()
    
    print("\n=== Aggregated Data (Today) with Topics ===")
    print(f"{'Time':<20} | {'Context':<15} | {'Topic':<30} | {'Dur(m)':<6} | {'Apps'}")
    print("-" * 100)
    for row in rows:
        # row: id, start, context, topic, duration, apps, details_count
        start = row[1]
        context = row[2]
        topic = row[3]
        # Truncate topic if too long
        if len(topic) > 28:
            topic = topic[:25] + "..."
            
        duration_min = round(row[4] / 60, 1)
        apps = row[5]
        print(f"{start:<20} | {context:<15} | {topic:<30} | {duration_min:<6} | {apps}")
        
    conn.close()

if __name__ == "__main__":
    print("Step 1: Loading raw data...")
    df = load_data()
    if not df.empty:
        print(f"Loaded {len(df)} raw records.")
        
        print("Step 2: Processing data...")
        sessions = intelligent_merge(df)
        
        print("Step 3: Saving to new DB...")
        save_to_new_db(sessions)
        
        print("Step 4: Displaying results...")
        show_results()
    else:
        print("No data found for today.")
