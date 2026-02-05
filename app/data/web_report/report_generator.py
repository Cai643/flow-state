# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import json

from app.data.core.database import get_db_connection, get_period_stats_db_connection, get_core_events_db_connection
from app.data.web_report.templates import REPORT_TEMPLATE

class ReportGenerator:
    """
    负责生成“深度专注力复盘报告”。
    流程：
    1. 获取数据 (Database)
    2. 计算衍生指标 (Algorithm)
    3. 调用 AI 生成核心洞察 (AI - 预留接口)
    4. 渲染模板 (Template)
    """

    def __init__(self):
        pass

    def generate_report(self, days: int = 3, ai_callback=None) -> str:
        """
        生成报告的主入口。
        :param days: 统计最近多少天的数据（默认3天）
        :param ai_callback: 一个函数，接收 context(dict) 并返回 {core_items: dict, encouragement: str}
                            如果为 None，则使用默认的占位符文本。
        :return: 渲染好的 Markdown 报告字符串
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        # 1. 获取基础数据
        data_context = self._fetch_data(start_date, end_date)
        
        # 2. 计算衍生指标 & 格式化数据
        formatted_data = self._process_data(data_context, days)
        
        # 3. AI 生成部分 (核心事项 + 致追梦者)
        ai_result = {"core_items": {}, "encouragement": "AI 正在思考中..."}
        if ai_callback:
            # 构造给 AI 的 Prompt Context
            ai_context = {
                "period": f"{start_date} to {end_date}",
                "total_focus_hours": formatted_data["total_focus_hours"],
                "willpower_wins": formatted_data["willpower_wins"],
                "peak_day": formatted_data["peak_day_info"],
                "daily_logs": formatted_data["daily_logs_for_ai"],
                "period_stats_rows": formatted_data.get("period_stats_rows", []),
                "top_apps": formatted_data.get("top_apps", "")
            }
            try:
                ai_result = ai_callback(ai_context)
            except Exception as e:
                print(f"[ReportGenerator] AI generation failed: {e}")
                ai_result = {
                    "core_items": {}, 
                    "encouragement": "致追梦者：数据表明你正在稳步前行。保持节奏，Flow State 就在前方。(AI 生成暂时不可用)"
                }

        # 4. 最终渲染
        return self._render_template(formatted_data, ai_result)

    def _fetch_data(self, start_date: date, end_date: date) -> Dict:
        """从数据库拉取原始数据"""
        data = {
            "daily_stats": [],
            "core_events": [],
            "window_sessions": [] # 用于更精确的巅峰时刻
        }
        
        s_str = start_date.strftime("%Y-%m-%d")
        e_str = end_date.strftime("%Y-%m-%d")

        # 1. Main DB: Daily Stats & Window Sessions
        with get_db_connection() as conn:
            # Daily Stats
            cursor = conn.execute("""
                SELECT date, total_focus_time, max_focus_streak, willpower_wins, efficiency_score 
                FROM daily_stats 
                WHERE date BETWEEN ? AND ?
                ORDER BY date ASC
            """, (s_str, e_str))
            data["daily_stats"] = [dict(row) for row in cursor.fetchall()]

            # Window Sessions (用于寻找具体的巅峰时刻时间段)
            # 这里简化处理：只找这段时间内持续时间最长的一次会话
            cursor = conn.execute("""
                SELECT start_time, end_time, duration, window_title, process_name
                FROM window_sessions
                WHERE date(start_time) BETWEEN ? AND ?
                ORDER BY duration DESC
                LIMIT 1
            """, (s_str, e_str))
            row = cursor.fetchone()
            if row:
                data["peak_session"] = dict(row)
            else:
                data["peak_session"] = None

        # 2. Core Events DB
        with get_core_events_db_connection() as conn:
            # Core Events (Top 1 per day, prioritize Focus but include Entertainment if significant)
            # 策略调整：不仅仅取 rank=1 的，而是获取前 2 名，方便后续逻辑判断是否要展示“娱乐”
            print(f"DEBUG: Fetching core events between {s_str} and {e_str}")
            cursor = conn.execute("""
                SELECT date, app_name, clean_title, total_duration, category 
                FROM core_events 
                WHERE date BETWEEN ? AND ? AND rank <= 3
                ORDER BY date ASC, rank ASC
            """, (s_str, e_str))
            
            # 将 Core Events 按日期分组
            raw_events = [dict(row) for row in cursor.fetchall()]
            print(f"DEBUG: Fetched {len(raw_events)} core events")
            
            events_by_date = {}
            for ev in raw_events:
                d = ev['date']
                try:
                    d_key = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
                except Exception:
                    d_key = str(d)
                if d_key not in events_by_date:
                    events_by_date[d_key] = []
                events_by_date[d_key].append(ev)
            
            data["core_events_map"] = events_by_date
            data["core_events"] = raw_events

        # 3. Period Stats DB
        with get_period_stats_db_connection() as conn:
            cursor = conn.execute("""
                SELECT date, total_focus, peak_hour, efficiency_score, daily_summary, focus_fragmentation_ratio, context_switch_freq 
                FROM period_stats 
                WHERE date BETWEEN ? AND ?
                ORDER BY date ASC
            """, (s_str, e_str))
            period_map = {}
            period_rows = []
            for row in cursor.fetchall():
                d = row["date"]
                try:
                    d_key = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
                except Exception:
                    d_key = str(d)
                period_map[d_key] = row["daily_summary"] or ""
                # sqlite3.Row does not support .get; use key checks
                keys = row.keys()
                period_rows.append({
                    "date": d_key,
                    "total_focus": row["total_focus"] or 0,
                    "peak_hour": row["peak_hour"] or 0,
                    "efficiency_score": row["efficiency_score"] or 0,
                    "daily_summary": row["daily_summary"] or "",
                    "focus_fragmentation_ratio": (row["focus_fragmentation_ratio"] if "focus_fragmentation_ratio" in keys else 0) or 0,
                    "context_switch_freq": (row["context_switch_freq"] if "context_switch_freq" in keys else 0) or 0
                })
            data["period_summary_map"] = period_map
            data["period_stats_rows"] = period_rows

        return data

    def _process_data(self, data: Dict, days: int) -> Dict:
        """处理和计算衍生数据"""
        daily_stats = data["daily_stats"]
        
        # 基础聚合
        total_focus_sec = sum(d["total_focus_time"] for d in daily_stats)
        total_wins = sum(d["willpower_wins"] for d in daily_stats)
        avg_efficiency = int(sum(d["efficiency_score"] for d in daily_stats) / len(daily_stats)) if daily_stats else 0
        
        total_focus_hours = round(total_focus_sec / 3600, 1)
        
        # 洞察计算
        # 假设：总活跃时长 ≈ 专注时长 / 0.68 (反推模板中的 68%) 
        # 或者如果有真实的总时长数据更好。这里暂时用简单的“专注占比”话术
        focus_ratio_insight = "占总活跃时长的 68% (估算)" # 待优化：需要真实总时长
        
        # 意志力挽回时间：假设每次挽回 5 分钟
        saved_mins = total_wins * 5
        willpower_insight = f"成功抵御了 {total_wins} 次短途走神，夺回了宝贵的 {saved_mins} 分钟"
        
        # 效能评级
        efficiency_level = "优秀" if avg_efficiency >= 80 else ("良好" if avg_efficiency >= 60 else "待提升")
        
        # 寻找巅峰日 (Focus Time 最长的一天)
        peak_day_info = {}
        if daily_stats:
            peak_day = max(daily_stats, key=lambda x: x["total_focus_time"])
            # 如果 date 是字符串，才转换；如果是 date 对象，直接使用
            if isinstance(peak_day["date"], str):
                peak_date_obj = datetime.strptime(peak_day["date"], "%Y-%m-%d")
            else:
                peak_date_obj = peak_day["date"]
            
            weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            
            # 尝试关联具体的巅峰时刻 (从 window_sessions)
            peak_session = data.get("peak_session")
            peak_desc = ""
            if peak_session and peak_session["start_time"]:
                # 确保 peak session 是在巅峰日发生的（这里简化，直接用最长会话）
                # 格式化时间段
                try:
                    if isinstance(peak_session["start_time"], str):
                        st = datetime.strptime(peak_session["start_time"], "%Y-%m-%d %H:%M:%S")
                        et = datetime.strptime(peak_session["end_time"], "%Y-%m-%d %H:%M:%S")
                    else:
                        st = peak_session["start_time"]
                        et = peak_session["end_time"]
                        
                    duration_min = int(peak_session["duration"] / 60)
                    peak_desc = f"特别是在 {st.strftime('%H:%M')} 至 {et.strftime('%H:%M')} 期间，你创造了令人印象深刻的“{duration_min}分钟心流”。"
                except Exception as e:
                    print(f"Error parsing peak session time: {e}")
            
            peak_day_info = {
                "date_str": f"{peak_day['date']} ({weekday_map[peak_date_obj.weekday()]})",
                "hours": round(peak_day["total_focus_time"] / 3600, 1),
                "desc_suffix": peak_desc
            }
        
        # 准备每日全景的数据 (Daily Rows)
        daily_rows_data = []
        daily_logs_for_ai = [] # 给 AI 用的精简版
        
        # 创建日期映射以便合并 Core Events
        # core_map = {row["date"]: row for row in data["core_events"]} # Old logic
        core_events_map = data.get("core_events_map", {})
        
        for stat in daily_stats:
            d_str = stat["date"]
            # 格式化日期： 2026-01-21 -> 1月21日
            if isinstance(d_str, str):
                dt = datetime.strptime(d_str, "%Y-%m-%d")
            else:
                dt = d_str
                # 将 d_str 统一转为字符串以便查表
                d_str = dt.strftime("%Y-%m-%d")
                
            fmt_date = f"{dt.month}月{dt.day}日"
            
            # 改进：不再只选一个，而是收集 Top 3 Focus + Top 2 Ent
            events = core_events_map.get(d_str, [])
            
            focus_items = [e for e in events if e['category'] == 'focus'][:3]
            ent_items = [e for e in events if e['category'] == 'entertainment'][:2]
            
            # 1. 构建详细上下文给 AI (用于生成精炼总结)
            items_desc_list = []
            for e in focus_items:
                dur_m = int(e['total_duration'] / 60)
                items_desc_list.append(f"[工作] {e['app_name']} - {e['clean_title']} ({dur_m}分钟)")
            
            for e in ent_items:
                dur_m = int(e['total_duration'] / 60)
                items_desc_list.append(f"[娱乐] {e['app_name']} - {e['clean_title']} ({dur_m}分钟)")
            
            items_context_str = "\n".join(items_desc_list)
            
            # 2. 构建 Fallback 显示 (当 AI 失败时)
            # 连贯短句: "主要X、Y（看Z）"
            fb_parts = []
            for e in focus_items[:2]:
                t = e['clean_title'][:6]
                if len(e['clean_title']) > 8: t = e['app_name'].split('.')[0]
                fb_parts.append(t)
            
            if ent_items:
                titles = []
                for e in ent_items[:2]:
                    t = e['clean_title'][:6]
                    if len(e['clean_title']) > 8:
                        t = e['app_name'].split('.')[0]
                    titles.append(t)
                ent_suffix = ''.join([f"，看{t}" for t in titles])
            else:
                ent_suffix = ""
                 
            if fb_parts:
                raw_display = "主要" + "，".join(fb_parts) + ent_suffix
            else:
                raw_display = "无主要活动"
            if raw_display == "无主要活动":
                ps = data.get("period_summary_map", {}).get(d_str, "")
                if ps:
                    raw_display = ps
            
            row_data = {
                "date": d_str,
                "fmt_date": fmt_date,
                "raw_core_item": raw_display, 
                "hours": round(stat["total_focus_time"] / 3600, 1),
                "longest_min": int(stat["max_focus_streak"] / 60)
            }
            daily_rows_data.append(row_data)
            
            daily_logs_for_ai.append({
                "date": fmt_date,
                "items_context": items_context_str, # 新字段：包含多条记录
                "hours": row_data["hours"]
            })

        # 提取主要阵地 (Top Apps)
        apps = {}
        for event in data["core_events"]:
            name = event["app_name"]
            if name:
                apps[name] = apps.get(name, 0) + event["total_duration"]
        top_apps_list = sorted(apps.items(), key=lambda x: x[1], reverse=True)[:3]
        top_apps_str = ",".join([k for k, v in top_apps_list])

        return {
            "start_date": daily_stats[0]["date"] if daily_stats else "",
            "end_date": daily_stats[-1]["date"] if daily_stats else "",
            "top_apps": top_apps_str,
            "total_focus_hours": total_focus_hours,
            "focus_ratio_insight": focus_ratio_insight,
            "willpower_wins": total_wins,
            "willpower_insight": willpower_insight,
            "efficiency_score": avg_efficiency,
            "efficiency_level": efficiency_level,
            "peak_day_info": peak_day_info,
            "daily_rows_data": daily_rows_data,
            "daily_logs_for_ai": daily_logs_for_ai,
            "period_stats_rows": data.get("period_stats_rows", [])
        }

    def _render_template(self, data: Dict, ai_result: Dict) -> str:
        """将数据填入模板"""
        
        # 1. 构建巅峰时刻描述
        peak_info = data.get("peak_day_info", {})
        if peak_info:
            peak_moment_desc = f"在 {peak_info.get('date_str')}，你贡献了 {peak_info.get('hours')} 小时的深度工作。\n当天主要致力于：{ai_result.get('peak_day_focus', '核心任务')}，{peak_info.get('desc_suffix')}"
        else:
            peak_moment_desc = "暂无足够数据生成巅峰时刻。"

        # 2. 构建每日全景行 (Daily Rows)
        rows_str = ""
        core_items_map = ai_result.get("core_items", {}) # AI 返回的 { "2026-01-21": "开发后端" }
        
        for row in data["daily_rows_data"]:
            # 优先使用 AI 生成的核心事项 (尝试多种 key)
            # 1. 完整日期 "2026-01-29"
            # 2. 格式化日期 "1月29日"
            # 3. 原始 Fallback "无主要活动"
            core_item = core_items_map.get(row["date"]) or core_items_map.get(row["fmt_date"]) or row["raw_core_item"]
            
            # Debug log
            # print(f"Processing row {row['date']}: AI={core_items_map.get(row['date'])}, Raw={row['raw_core_item']}")

            # 截断过长的文本
            # if len(core_item) > 20: core_item = core_item[:18] + "..."
            # 允许更长一点，毕竟现在包含了娱乐
            if len(core_item) > 32: core_item = core_item[:30] + "..."
            
            line = (
                f"<tr>"
                f"<td style='padding:6px 8px; border-bottom:1px solid #eee;'>{row['fmt_date']}</td>"
                f"<td style='padding:6px 8px; border-bottom:1px solid #eee;'>{core_item}</td>"
                f"<td style='padding:6px 8px; border-bottom:1px solid #eee;'>{row['hours']} h</td>"
                f"<td style='padding:6px 8px; border-bottom:1px solid #eee;'>{row['longest_min']} min</td>"
                f"</tr>"
            )
            rows_str += line

        # 3. 填充主模板（安全格式化，缺失字段默认空字符串，避免 KeyError）
        class SafeDict(dict):
            def __missing__(self, key):
                return ""
        fmt_map = {
            "start_date": data.get("start_date", ""),
            "end_date": data.get("end_date", ""),
            "days": len(data.get("daily_rows_data", [])),
            "top_apps": data.get("top_apps", ""),
            "total_focus_hours": data.get("total_focus_hours", 0),
            "focus_ratio_insight": data.get("focus_ratio_insight", ""),
            "willpower_wins": data.get("willpower_wins", 0),
            "willpower_insight": data.get("willpower_insight", ""),
            "efficiency_score": data.get("efficiency_score", 0),
            "efficiency_level": data.get("efficiency_level", ""),
            "peak_moment_desc": peak_moment_desc or "",
            "daily_rows": rows_str or "",
            "ai_encouragement": ai_result.get("encouragement", "保持专注，继续前行！")
        }
        return REPORT_TEMPLATE.format_map(SafeDict(fmt_map))
