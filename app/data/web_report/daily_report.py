import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from app.data.dao.analysis_dao import AnalysisDAO
from app.service.detector.detector_logic import analyze # Assuming this is your local AI interface

def generate_deep_focus_report(start_date, end_date):
    print(f"Generating report for {start_date} to {end_date}...")
    
    # 1. Fetch Data via DAO
    focus_stats = AnalysisDAO.get_focus_time_stats(start_date, end_date)
    willpower_wins = AnalysisDAO.get_willpower_victories(start_date, end_date)
    daily_breakdown = AnalysisDAO.get_daily_breakdown(start_date, end_date)
    best_day = AnalysisDAO.get_best_day(daily_breakdown)
    top_apps = AnalysisDAO.get_top_apps(start_date, end_date)
    
    # 2. Format Basic Data
    total_focus_hours = round(focus_stats['focus_seconds'] / 3600, 1)
    focus_ratio_percent = int(focus_stats['focus_ratio'] * 100)
    
    app_names = ",".join([app['app'] for app in top_apps])
    
    # Efficiency Index Calculation (Simple Algorithm)
    # Base 60 + (Focus Ratio * 20) + (Willpower Wins * 2)
    # Cap at 100
    efficiency_score = 60 + (focus_stats['focus_ratio'] * 20) + (willpower_wins * 2)
    efficiency_score = min(100, int(efficiency_score))
    efficiency_eval = "优秀" if efficiency_score >= 80 else ("良好" if efficiency_score >= 60 else "需加油")

    # 3. AI Processing for "Top Activity" Summarization (Loop through days)
    print("AI Processing: Summarizing daily activities...")
    for day in daily_breakdown:
        raw_summary = day['top_activity_raw']
        if raw_summary and raw_summary != "无记录":
            # Call AI to summarize
            # Limit input length to save tokens
            short_input = raw_summary[:300] 
            prompt = f"请将以下活动记录概括为一件事（5-10个字），例如'开发核心功能'。记录：{short_input}"
            try:
                # Use json_mode=False for simple text return
                # summary = analyze(prompt, system_prompt="你是一个精准的概括助手。", json_mode=False)
                # Clean up AI output (remove quotes, etc.)
                # day['ai_summary'] = summary.strip().replace('"', '').replace("'", "")
                
                # Temporary: Skip AI to speed up verification
                day['ai_summary'] = raw_summary[:20] + "..."
            except Exception as e:
                print(f"AI Summary failed for {day['date']}: {e}")
                day['ai_summary'] = raw_summary[:20] + "..."
        else:
            day['ai_summary'] = "无主要活动"

    # 4. AI Processing for "Encouragement"
    print("AI Processing: Generating encouragement...")
    
    # Construct a minimal data context for AI
    best_day_str = f"{best_day['date']} ({best_day['focus_hours']}h)" if best_day else "N/A"
    
    context_str = f"""
    周期: {start_date}至{end_date}
    专注总时长: {total_focus_hours}小时
    意志力胜利: {willpower_wins}次
    最佳单日: {best_day_str}
    最长心流: {best_day['max_streak_minutes'] if best_day else 0}分钟
    """
    
    encourage_prompt = f"""
    基于以下数据写一段致辞（100字内），风格热血极客。
    数据：{context_str}
    """
    
    try:
        # encouragement = analyze(encourage_prompt, system_prompt="你是一个热血的效率教练。", json_mode=False)
        # Temporary: Skip AI
        encouragement = f"数据证明了你的努力。在{best_day_str.split(' ')[0]}，你创造了惊人的记录。保持专注，Flow State 已触手可及。"
    except Exception as e:
        encouragement = "保持专注，继续前行！数据证明了你的努力。"

    # 5. Assemble Markdown Report
    report = f"""
# 📊 深度专注力复盘报告 (Deep Focus Review) 
📅 周期：{start_date} 至 {end_date} (共 {(datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1} 天) 
🏰 主要阵地：{app_names}

## 1. 核心效能仪表盘 (Core Performance) 
| 核心指标 | 数值 | 洞察 |
| :--- | :--- | :--- |
| ⏳ 专注总时长 | **{total_focus_hours} 小时** | 占总活跃时长的 {focus_ratio_percent}% |
| 🛡️ 意志力胜利 | **{willpower_wins} 次** | 成功抵御了 {willpower_wins} 次短途走神，并在 5 分钟内重回工作。 |
| ⚡ 效能指数 | **{efficiency_score} / 100** | {efficiency_eval} |

🏆 **巅峰时刻 (Best Day)**： 
在 {best_day['date'] if best_day else 'N/A'}，你贡献了 {best_day['focus_hours'] if best_day else 0} 小时的深度工作。

## 2. 每日专注全景 (Daily Breakdown) 
| 日期 | 🎯 核心事项 (Top Activity) | ⏱️ 投入时长 | 🔥 最长持续 (Max Streak) |
| :--- | :--- | :--- | :--- |
"""
    
    for day in daily_breakdown:
        report += f"| {day['date']} | {day['ai_summary']} | {day['focus_hours']} h | {day['max_streak_minutes']} min |\n"

    report += f"""
## 3. 致追梦者 (Encouragement) 
> "{encouragement.strip()}"
"""

    return report

if __name__ == "__main__":
    # Example usage
    report = generate_deep_focus_report("2026-01-21", "2026-01-23")
    print("\n" + "="*30 + " REPORT PREVIEW " + "="*30 + "\n")
    print(report)
    
    # Save to file
    with open("focus_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\nReport saved to focus_report.md")
