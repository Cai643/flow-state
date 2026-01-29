# -*- coding: utf-8 -*-

# 📊 深度专注力复盘报告
REPORT_TEMPLATE = """
<div class=\"report-card\"><div class=\"report-body\">
## 近{days}天报告总结
📅 周期：{start_date} 至 {end_date} (共 {days} 天)
🏰 主要阵地：{top_apps}

## 核心效能仪表盘
<table style="width:100%; border-collapse:collapse;">
<thead>
<tr>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">指标</th>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">数值</th>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">洞察</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">⏳ 专注总时长</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{total_focus_hours} 小时</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{focus_ratio_insight}</td>
</tr>
<tr>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">🛡️ 意志力胜利</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{willpower_wins} 次</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{willpower_insight}</td>
</tr>
<tr>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">⚡ 效能指数</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{efficiency_score} / 100</td>
<td style="padding:6px 8px; border-bottom:1px solid #eee;">{efficiency_level}</td>
</tr>
</tbody>
</table>

<div class=\"peak-banner\">🏆 巅峰时刻 ：<br>{peak_moment_desc}</div>

## 每日专注全景
<table style="width:100%; border-collapse:collapse;">
<thead>
<tr>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">日期</th>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">🎯 核心事项</th>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">⏱️ 投入时长</th>
<th style="text-align:left; padding:6px 8px; border-bottom:1px solid #ddd;">🔥 最长持续</th>
</tr>
</thead>
<tbody>
{daily_rows}
</tbody>
</table>

## 致追梦的我
{ai_encouragement}
</div></div>
"""
