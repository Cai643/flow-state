from datetime import datetime, timedelta
from app.data.dao.focus_dao import fetch_records_by_date

def consolidate_logs(date_str: str, max_gap_sec=30):
    """
    离线聚合，将临近的、状态相同的碎片（即便分散存储也会合并成连续大块）
    :param max_gap_sec: 允许最大间隔秒数，超过断为新段落
    :return: List[dict]，每段都是 {status, start, end, duration_min}
    """
    raw = fetch_records_by_date(date_str)
    if not raw:
        return []

    refined = []
    cur = None
    FMT = "%Y-%m-%dT%H:%M:%S"
    for rec in raw:
        status, start_str, dur = rec
        start_dt = datetime.strptime(start_str, FMT)
        end_dt = start_dt + timedelta(seconds=dur)

        if cur is None:
            cur = [status, start_dt, end_dt]
        else:
            # 状态相同且本段的start和上一段end的间隔小于max_gap_sec，则合并
            last_status, last_start, last_end = cur
            gap = (start_dt - last_end).total_seconds()
            if status == last_status and gap <= max_gap_sec:
                cur[2] = end_dt  # 合并进当前段
            else:
                refined.append(cur)
                cur = [status, start_dt, end_dt]
    if cur:
        refined.append(cur)

    # [status_code, start_dt, end_dt] -> 输出为聚合的时间段
    out = []
    for item in refined:
        status, st, et = item
        # 计算分钟，最少显示为1（避免0分钟渲染不出效果！）
        minute = max(1, int(round((et - st).total_seconds() / 60)))
        out.append({
            "status": status,
            "start": st.strftime("%H:%M"),
            "end": et.strftime("%H:%M"),
            "duration_min": minute
        })
    return out

def get_daily_summary(date_str: str):
    """
    汇总统计：当天专注/娱乐总时长(分钟)，以及重组后的时间段（提纯大块，绘图可用）
    """
    segments = consolidate_logs(date_str)
    total_focus = sum(s["duration_min"] for s in segments if s["status"] == 1)
    total_play = sum(s["duration_min"] for s in segments if s["status"] == 2)
    # 输出提纯后的timeline（segments）
    return {
        "date": date_str,
        "total_focus_min": total_focus,
        "total_play_min": total_play,
        "timeline": segments
    }