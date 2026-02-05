import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.data.core.database import get_db_connection, get_period_stats_db_connection, get_core_events_db_connection, init_db

def calculate_period_stats(target_date):
    """
    计算指定日期的核心指标：
    1. 总专注时长
    2. 最长心流
    3. 意志力胜利次数
    4. 黄金时段
    5. 效能指数 (简单算法)
    """
    print(f"Calculating stats for {target_date}...")
    
    start_ts = f"{target_date} 00:00:00"
    end_ts = f"{target_date} 23:59:59"
    
    # 变量初始化，确保跨作用域可用
    all_rows = []
    focus_rows = []
    total_focus = 0
    max_streak = 0
    willpower_wins = 0
    peak_hour = 0
    score = 0
    focus_frag_ratio = 0.0
    switch_freq = 0.0
    
    # --- Phase 1: Main DB (Window Sessions & Daily Stats) ---
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # --- 1. 基础数据获取 (from window_sessions) ---
        # 获取当天所有工作/专注记录
        cursor.execute('''
            SELECT start_time, duration, status
            FROM window_sessions
            WHERE start_time BETWEEN ? AND ?
            ORDER BY start_time ASC
        ''', (start_ts, end_ts))
        
        all_rows = cursor.fetchall()
        
        # 筛选专注记录
        focus_rows = [r for r in all_rows if r['status'] in ['work', 'focus']]
        
        # --- Source Sync: Fetch reliable metrics from daily_stats ---
        # 优先使用 daily_stats 的数据，因为它处理了跨天且是实时累加的
        cursor.execute('''
            SELECT total_focus_time, max_focus_streak 
            FROM daily_stats 
            WHERE date = ?
        ''', (target_date,))
        daily_stat_row = cursor.fetchone()
        
        # [Fix] 优先使用 daily_stats 的总时长，但重新计算 max_streak
        # 原因：daily_stats 中的 max_focus_streak 是实时更新的，可能受旧脏数据影响（如之前的 515min 异常值）。
        # 而 window_sessions 已经清理过，重新计算更准确。
        
        if daily_stat_row:
            total_focus = daily_stat_row['total_focus_time']
            # max_streak = daily_stat_row['max_focus_streak'] # <--- 移除这行，改用重新计算
            print(f"  [Sync] Using daily_stats for Total Focus: {total_focus}s")
        else:
            total_focus = sum(r['duration'] for r in focus_rows)
            print("  [Sync] daily_stats missing, calculating from window_sessions...")

        # [Re-calculate Max Streak] 强制基于当前的 window_sessions 重新计算
        # 确保数据清理后的准确性
        current_streak = 0
        last_end_time = None
        for r in focus_rows:
            if isinstance(r['start_time'], str):
                start = datetime.strptime(r['start_time'], "%Y-%m-%d %H:%M:%S")
            else:
                start = r['start_time']
            dur = r['duration']
            
            if last_end_time:
                diff = (start - last_end_time).total_seconds()
                # 如果间隔小于 2 分钟，视为连续
                if diff < 120: 
                    current_streak += dur
                else:
                    max_streak = max(max_streak, current_streak)
                    current_streak = dur
            else:
                current_streak = dur
            last_end_time = start + timedelta(seconds=dur)
        max_streak = max(max_streak, current_streak)
        print(f"  [Re-calc] Max Streak re-calculated from sessions: {max_streak}s ({int(max_streak/60)} min)")
        
        # 将重算的 max_streak 回写到 daily_stats (修正旧数据)
        cursor.execute('''
            UPDATE daily_stats 
            SET max_focus_streak = ? 
            WHERE date = ?
        ''', (max_streak, target_date))
        conn.commit()
        
        # --- Metric 3: Willpower Wins ---
        # Willpower Wins 必须通过回溯 window_sessions 计算，因为 daily_stats 没有存这个复杂指标
        state = 0 
        # 0: Seek Focus > 300s
        # 1: Found Focus, Seek Distraction
        # 2: Found Distraction < 300s, Seek Focus > 300s (Recovery)
        
        # 重新遍历所有行 (包含娱乐)
        for r in all_rows:
            status = r['status']
            dur = r['duration']
            is_focus = status in ['work', 'focus']
            is_distraction = status in ['entertainment', 'other', 'unknown']
            
            if state == 0:
                if is_focus and dur > 300: state = 1
            elif state == 1:
                if is_distraction:
                    if dur < 300: state = 2
                    else: state = 0 # Distraction too long
                elif is_focus: pass # Continue focus
            elif state == 2:
                if is_focus:
                    willpower_wins += 1
                    state = 1 if dur > 300 else 0
                elif is_distraction:
                    state = 0 # Double distraction
                    
        # --- Metric 4: Peak Hour ---
        # 统计每个小时的专注时长
        hour_stats = {}
        for r in focus_rows:
            # 同样需要确保是 datetime
            if isinstance(r['start_time'], str):
                start = datetime.strptime(r['start_time'], "%Y-%m-%d %H:%M:%S")
            else:
                start = r['start_time']
                
            h = start.hour
            if h not in hour_stats: hour_stats[h] = 0
            hour_stats[h] += r['duration']
            
        peak_hour = max(hour_stats, key=hour_stats.get) if hour_stats else 0
        
        # --- Metric 5: Efficiency Score ---
        # 基础分60 + (时长分: 每小时+5分) + (意志力分: 每次+2分)
        # 上限 100
        hours = total_focus / 3600
        score = 60 + (hours * 5) + (willpower_wins * 2)
        score = min(100, int(score))

        # --- Metric 6: Advanced Metrics ---
        # 6.1 Focus/Fragmentation Ratio (专注/碎片比)
        # 计算平均专注会话时长 和 平均娱乐会话时长
        avg_focus_dur = 0
        if focus_rows:
            avg_focus_dur = sum(r['duration'] for r in focus_rows) / len(focus_rows)
            
        ent_rows = [r for r in all_rows if r['status'] in ['entertainment', 'other', 'unknown']]
        avg_ent_dur = 0
        if ent_rows:
            avg_ent_dur = sum(r['duration'] for r in ent_rows) / len(ent_rows)
            
        # Ratio: 如果没有娱乐，给一个高分 (e.g. 10.0)
        # 如果有娱乐，Ratio = AvgFocus / AvgEnt
        if avg_ent_dur > 0:
            focus_frag_ratio = round(avg_focus_dur / avg_ent_dur, 2)
        else:
            focus_frag_ratio = 10.0 if avg_focus_dur > 0 else 0.0
            
        # 6.2 Context Switch Frequency (切换频率)
        # 总切换次数 / 总活跃小时数
        # 活跃小时数 = (最后一条记录结束 - 第一条记录开始) / 3600
        if all_rows:
            # 获取最早和最晚时间
            start_dt = all_rows[0]['start_time']
            end_dt = all_rows[-1]['start_time']
            if isinstance(start_dt, str): start_dt = datetime.strptime(start_dt, "%Y-%m-%d %H:%M:%S")
            if isinstance(end_dt, str): end_dt = datetime.strptime(end_dt, "%Y-%m-%d %H:%M:%S")
            
            active_hours = (end_dt - start_dt).total_seconds() / 3600
            total_switches = len(all_rows)
            
            if active_hours > 0.5: # 至少活跃半小时才算
                switch_freq = round(total_switches / active_hours, 1)
            else:
                switch_freq = 0

    # --- Metric 7: Daily Summary (from Core Events DB) ---
    # 改进策略：聚合 Top 3 Focus + Top 2 Entertainment
    # 目标：30字以内的精简摘要
    
    daily_summary = ""
    
    with get_core_events_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. 获取 Focus (Top 3)
        cursor.execute('''
            SELECT app_name, clean_title, total_duration 
            FROM core_events 
            WHERE date = ? AND category = 'focus'
            ORDER BY rank ASC 
            LIMIT 3
        ''', (target_date,))
        focus_events = cursor.fetchall()
        
        # 2. 获取 Entertainment (Top 2)
        cursor.execute('''
            SELECT app_name, clean_title, total_duration 
            FROM core_events 
            WHERE date = ? AND category = 'entertainment'
            ORDER BY rank ASC 
            LIMIT 2
        ''', (target_date,))
        ent_events = cursor.fetchall()
        
        items = []
        
        # 辅助函数：生成极简标题
        def get_short_title(ev):
            t = ev['clean_title']
            a = ev['app_name']
            # 如果标题太长或无意义，用 App 名
            if len(t) > 8 or t == "Unknown":
                return a.split('.')[0] # 去掉 .exe
            return t[:6] # 截断
            
        # 优先加入 Focus Top 1 & 2
        for ev in focus_events[:2]:
            t = get_short_title(ev)
            items.append(t)
            
        # 加入 Ent Top 1 (如果有时长显著)
        if ent_events:
            ev = ent_events[0]
            if ev['total_duration'] > 600: # 至少10分钟
                t = get_short_title(ev)
                items.append(f"({t})") # 娱乐用括号标注
                
        # 如果字数还够，加入 Focus Top 3
        if len(" ".join(items)) < 20 and len(focus_events) > 2:
             t = get_short_title(focus_events[2])
             items.append(t)
             
        # 组合并截断
        daily_summary = " ".join(items)
        if len(daily_summary) > 30:
            daily_summary = daily_summary[:29] + "…"
            
        if not daily_summary:
            daily_summary = "无主要活动"
            
    # --- Metric 8: AI Insight Generation ---
    insights = []
    
    # 1. 状态判断 (基于 Ratio & Freq)
    if focus_frag_ratio > 1.2 and switch_freq < 10:
        insights.append("深度心流态")
    elif focus_frag_ratio < 0.8 and switch_freq > 20:
        insights.append("碎片化焦虑")
    elif focus_frag_ratio > 1.0 and switch_freq > 15:
        insights.append("高压多任务")
    else:
        insights.append("常规工作态")
        
    # 2. 补充标签
    if max_streak > 5400: # 90 min
        insights.append("铁人模式")
    if willpower_wins > 8:
        insights.append("意志力爆发")
    if score == 100:
        insights.append("完美表现")
        
    ai_insight = " | ".join(insights)
    
    # --- Save to DB (Period Stats DB) ---
    with get_period_stats_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM period_stats WHERE date = ?", (target_date,))
        cursor.execute('''
            INSERT INTO period_stats (date, total_focus, max_streak, willpower_wins, peak_hour, efficiency_score, daily_summary, focus_fragmentation_ratio, context_switch_freq, ai_insight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (target_date, total_focus, max_streak, willpower_wins, peak_hour, score, daily_summary, focus_frag_ratio, switch_freq, ai_insight))
        
        conn.commit()
        print(f"Saved stats for {target_date}: Focus={total_focus}s, Insight='{ai_insight}'")

def run_backfill(days=3):
    init_db()
    today = datetime.now().date()
    # 强制包含 2026-01-21 用于演示
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    if '2026-01-21' not in dates:
        dates.append('2026-01-21')
        
    for d_str in dates:
        calculate_period_stats(d_str)

if __name__ == "__main__":
    run_backfill(4) # 覆盖 21, 22, 23, 24
