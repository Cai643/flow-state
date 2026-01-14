from app.data import ActivityDAO

def summarize_activity(date_str: str) -> dict:
    """
    聚合一天所有段，统计每种状态的总时长（秒），并输出协议格式的timeline
    """
    logs = ActivityDAO.get_logs_by_date(date_str)
    total = {
        "focus": 0,
        "entertainment": 0,
        "idle": 0,
        "distracted": 0
    }
    timeline = []
    for row in logs:
        status = row["status"]
        duration = row["duration"]
        total[status] += duration
        timeline.append({
            "status": status,
            "timestamp": row["timestamp"],
            "duration": duration
        })
    # 输出合计时间，以分钟为单位展示。如果需要秒详单可前端自己除以60。
    return {
        "date": date_str,
        "timeline": timeline,
        "focus_time_min": int(total["focus"] / 60),
        "entertainment_time_min": int(total["entertainment"] / 60),
        "idle_time_min": int(total["idle"] / 60),
        "distracted_time_min": int(total["distracted"] / 60)
    }