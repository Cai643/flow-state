# -*- coding: utf-8 -*-

REPORT_TEMPLATE = """📊 深度专注力复盘报告
📅 周期：{start_date} 至 {end_date} (共 {days} 天)
🏰 主要阵地：{top_apps}

1. 核心效能仪表盘
 核心指标 \t 数值 \t 洞察
 ⏳ 专注总时长 \t {total_focus_hours} 小时 \t {focus_ratio_insight}
 🛡️ 意志力胜利 \t {willpower_wins} 次 \t {willpower_insight}
 ⚡ 效能指数 \t {efficiency_score} / 100 \t {efficiency_level}

🏆 巅峰时刻 ：
{peak_moment_desc}

2. 每日专注全景
 日期 \t 🎯 核心事项 \t ⏱️ 投入时长 \t 🔥 最长持续
{daily_rows}
(注：核心事项取自当天投入时间最长的项目或行为)

3. 致追梦者 (Encouragement)
{ai_encouragement}
"""
